"""
Integration tests for Diet NFL Betting Service

Tests complete workflows and interactions between components
including authentication, betting, data updates, and scheduling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models import User, Game, Bet, Transaction
from app.services.espn_service import ESPNService
from app.services.bet_validator import BetValidator
from app.services.scheduler import SchedulerService


@pytest.mark.integration
class TestCompleteWorkflows:
    """Test complete user workflows from end to end"""
    
    def test_complete_betting_workflow(self, app, client, mock_discord_oauth, mock_discord_user):
        """Test complete workflow: login → view games → place bet → view bet"""
        with app.app_context():
            # Step 1: User authentication via Discord
            with patch('app.routes.auth.discord.fetch_user', return_value=mock_discord_user):
                response = client.get('/auth/discord/callback?code=test_code')
                # Should redirect after successful auth
                assert response.status_code == 302
            
            # Step 2: Create a game for betting
            game = Game(
                espn_game_id='integration_test_game',
                week=1,
                season=2024,
                home_team='Kansas City Chiefs',
                away_team='Detroit Lions',
                game_time=datetime.utcnow() + timedelta(days=1),
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Step 3: Set up authenticated session
            user = User.query.filter_by(discord_id=str(mock_discord_user.id)).first()
            with client.session_transaction() as sess:
                sess['discord_user_id'] = user.discord_id
            
            # Step 4: View available games
            response = client.get('/betting/games')
            assert response.status_code == 200
            assert b'Kansas City Chiefs' in response.data
            assert b'Detroit Lions' in response.data
            
            # Step 5: Access bet placement form
            response = client.get(f'/betting/place/{game.id}')
            assert response.status_code == 200
            assert b'Place Your Bet' in response.data
            
            # Step 6: Place a bet
            response = client.post(f'/betting/place/{game.id}', data={
                'team_picked': 'Kansas City Chiefs',
                'wager_amount': '100.00'
            })
            assert response.status_code == 302  # Redirect to bet view
            
            # Step 7: Verify bet was created and user balance updated
            bet = Bet.query.filter_by(user_id=user.id, game_id=game.id).first()
            assert bet is not None
            assert bet.team_picked == 'Kansas City Chiefs'
            assert bet.wager_amount == 100.0
            
            updated_user = User.query.get(user.id)
            assert updated_user.balance == 9900.0  # 10000 - 100
            
            # Step 8: View bet details
            response = client.get(f'/betting/bet/{bet.id}')
            assert response.status_code == 200
            assert b'Kansas City Chiefs' in response.data
            assert b'$100.00' in response.data
    
    def test_espn_data_to_bet_settlement_workflow(self, app, sample_user, mock_espn_api):
        """Test workflow: ESPN data fetch → game creation → bet placement → game completion → settlement"""
        with app.app_context():
            # Step 1: ESPN service fetches and creates games
            espn_service = ESPNService()
            
            # Mock ESPN API response with completed game
            completed_game_response = {
                'events': [{
                    'id': '401547441',
                    'name': 'Green Bay Packers at Chicago Bears',
                    'date': (datetime.utcnow() - timedelta(hours=3)).isoformat() + 'Z',
                    'status': {'type': {'name': 'Final'}},
                    'competitions': [{
                        'competitors': [
                            {
                                'homeAway': 'home',
                                'team': {'displayName': 'Chicago Bears', 'abbreviation': 'CHI'},
                                'score': 17
                            },
                            {
                                'homeAway': 'away', 
                                'team': {'displayName': 'Green Bay Packers', 'abbreviation': 'GB'},
                                'score': 24
                            }
                        ]
                    }]
                }]
            }
            
            with patch.object(espn_service, '_make_request', return_value=completed_game_response):
                result = espn_service.fetch_and_update_current_week()
                assert result['success'] is True
                assert result['created'] >= 1
            
            # Step 2: Verify game was created
            game = Game.query.filter_by(espn_game_id='401547441').first()
            assert game is not None
            assert game.status == 'final'
            assert game.winner == 'Green Bay Packers'
            assert game.home_score == 17
            assert game.away_score == 24
            
            # Step 3: Simulate bet that was placed before game completion
            bet = Bet(
                user_id=sample_user.id,
                game_id=game.id,
                team_picked='Green Bay Packers',  # Winning team
                wager_amount=100.0,
                potential_payout=200.0,
                status='pending'
            )
            db.session.add(bet)
            db.session.commit()
            
            # Step 4: Simulate bet settlement (would be done by scheduler)
            bet.settle(game.winner)
            db.session.commit()
            
            # Step 5: Verify bet settlement
            assert bet.status == 'won'
            assert bet.actual_payout == 200.0
            assert bet.settled_at is not None
    
    def test_scheduler_espn_integration_workflow(self, app, mock_espn_api):
        """Test scheduler automatically triggering ESPN updates"""
        with app.app_context():
            # Step 1: Create and configure scheduler
            scheduler = SchedulerService(app)
            
            # Step 2: Add ESPN update job
            job = scheduler.add_espn_update_job('test_integration_job', 1)  # 1 minute interval
            assert job is not None
            
            # Step 3: Manually trigger the job function to simulate scheduled execution
            with patch('app.services.espn_service.update_nfl_games') as mock_update:
                mock_update.return_value = {
                    'success': True,
                    'games_processed': 1,
                    'created': 1,
                    'updated': 0
                }
                
                # Execute the job function
                job.func()
                
                # Verify ESPN update was called
                mock_update.assert_called_once()
            
            # Step 4: Clean up
            scheduler.shutdown()
    
    def test_concurrent_betting_workflow(self, app, client, sample_games):
        """Test multiple users betting on the same game simultaneously"""
        with app.app_context():
            bettable_game = None
            for game in sample_games:
                if game.is_bettable:
                    bettable_game = game
                    break
            
            assert bettable_game is not None
            
            # Create multiple users
            users = []
            for i in range(3):
                user = User(
                    discord_id=f'concurrent_user_{i}',
                    username=f'concurrentuser{i}',
                    balance=5000.0
                )
                users.append(user)
                db.session.add(user)
            db.session.commit()
            
            # Each user places a bet
            validator = BetValidator()
            bets = []
            
            for i, user in enumerate(users):
                bet_data = {
                    'team_picked': bettable_game.home_team if i % 2 == 0 else bettable_game.away_team,
                    'wager_amount': 100.0 + (i * 50)  # Different amounts
                }
                
                bet = validator.validate_and_create_bet(bet_data, user, bettable_game)
                bets.append(bet)
            
            # Verify all bets were placed successfully
            assert len(bets) == 3
            
            # Verify game statistics updated correctly
            updated_game = Game.query.get(bettable_game.id)
            assert updated_game.total_bets == 3
            assert updated_game.total_wagered == 450.0  # 100 + 150 + 200
            
            # Verify user balances updated
            for i, user in enumerate(users):
                updated_user = User.query.get(user.id)
                expected_balance = 5000.0 - (100.0 + (i * 50))
                assert updated_user.balance == expected_balance


@pytest.mark.integration 
class TestErrorHandlingWorkflows:
    """Test error handling and edge cases in complete workflows"""
    
    def test_betting_after_game_starts_workflow(self, app, client, authenticated_session):
        """Test attempting to bet after game has started"""
        with app.app_context():
            # Create a game that has already started
            started_game = Game(
                espn_game_id='started_game_test',
                week=1,
                season=2024,
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow() - timedelta(hours=1),
                status='in_progress'
            )
            db.session.add(started_game)
            db.session.commit()
            
            # Attempt to place bet
            response = authenticated_session.post(f'/betting/place/{started_game.id}', data={
                'team_picked': 'Team A',
                'wager_amount': '100.00'
            })
            
            # Should redirect due to game no longer being bettable
            assert response.status_code == 302
            
            # No bet should be created
            bet_count = Bet.query.filter_by(game_id=started_game.id).count()
            assert bet_count == 0
    
    def test_insufficient_balance_workflow(self, app, authenticated_session, bettable_game):
        """Test betting with insufficient balance"""
        with app.app_context():
            # Attempt to bet more than balance
            response = authenticated_session.post(f'/betting/place/{bettable_game.id}', data={
                'team_picked': bettable_game.home_team,
                'wager_amount': '50000.00'  # More than user's balance
            })
            
            # Should stay on betting page with error
            assert response.status_code == 200
            assert b'Insufficient balance' in response.data
            
            # No bet should be created
            bet_count = Bet.query.filter_by(game_id=bettable_game.id).count()
            assert bet_count == 0
    
    def test_duplicate_bet_prevention_workflow(self, app, authenticated_session, sample_user, bettable_game):
        """Test prevention of duplicate bets on same game"""
        with app.app_context():
            # Place first bet
            validator = BetValidator()
            bet_data = {
                'team_picked': bettable_game.home_team,
                'wager_amount': 100.0
            }
            first_bet = validator.validate_and_create_bet(bet_data, sample_user, bettable_game)
            
            # Attempt to place second bet on same game
            response = authenticated_session.get(f'/betting/place/{bettable_game.id}')
            # Should redirect to existing bet view
            assert response.status_code == 302
            assert f'/betting/bet/{first_bet.id}' in response.location
    
    def test_espn_api_failure_workflow(self, app):
        """Test handling of ESPN API failures"""
        with app.app_context():
            espn_service = ESPNService()
            
            # Mock API failure
            with patch.object(espn_service, '_make_request', side_effect=Exception("API Error")):
                result = espn_service.fetch_and_update_current_week()
                
                assert result['success'] is False
                assert 'error' in result
                assert result['games_processed'] == 0
    
    def test_scheduler_job_failure_workflow(self, app):
        """Test scheduler handling of job failures"""
        with app.app_context():
            scheduler = SchedulerService(app)
            
            # Add job that will fail
            job = scheduler.add_espn_update_job('failing_job', 1)
            
            # Mock ESPN service to fail
            with patch('app.services.espn_service.update_nfl_games', side_effect=Exception("Service Error")):
                # Job should handle exception gracefully
                try:
                    job.func()
                    # Should not raise exception
                except Exception:
                    pytest.fail("Job should handle exceptions gracefully")
            
            scheduler.shutdown()


@pytest.mark.integration
class TestDataIntegrityWorkflows:
    """Test data integrity across the complete system"""
    
    def test_transaction_rollback_on_bet_failure(self, app, sample_user, bettable_game):
        """Test database rollback when bet creation fails"""
        with app.app_context():
            original_balance = sample_user.balance
            
            validator = BetValidator()
            bet_data = {
                'team_picked': bettable_game.home_team,
                'wager_amount': 100.0
            }
            
            # Mock database error during bet creation
            with patch.object(db.session, 'commit', side_effect=Exception("Database error")):
                with pytest.raises(Exception):
                    validator.create_bet(bet_data, sample_user, bettable_game)
                
                # User balance should not be changed due to rollback
                db.session.refresh(sample_user)
                assert sample_user.balance == original_balance
                
                # No bet should be created
                bet_count = Bet.query.filter_by(user_id=sample_user.id).count()
                assert bet_count == 0
    
    def test_game_update_preserves_bet_integrity(self, app, sample_user, bettable_game, sample_bet):
        """Test that game updates don't affect existing bet integrity"""
        with app.app_context():
            original_bet_data = {
                'team_picked': sample_bet.team_picked,
                'wager_amount': sample_bet.wager_amount,
                'status': sample_bet.status
            }
            
            # Update game data (simulate ESPN update)
            bettable_game.status = 'in_progress'
            bettable_game.home_score = 7
            bettable_game.away_score = 3
            db.session.commit()
            
            # Verify bet data unchanged
            db.session.refresh(sample_bet)
            assert sample_bet.team_picked == original_bet_data['team_picked']
            assert sample_bet.wager_amount == original_bet_data['wager_amount']
            assert sample_bet.status == original_bet_data['status']
    
    def test_user_statistics_consistency(self, app, sample_user, bettable_game):
        """Test user statistics remain consistent across operations"""
        with app.app_context():
            initial_total_bets = sample_user.total_bets
            initial_balance = sample_user.balance
            
            # Place multiple bets
            validator = BetValidator()
            
            # Create additional games for multiple bets
            games = []
            for i in range(3):
                game = Game(
                    espn_game_id=f'stats_test_game_{i}',
                    week=1,
                    season=2024,
                    home_team=f'Home Team {i}',
                    away_team=f'Away Team {i}',
                    game_time=datetime.utcnow() + timedelta(days=i+1),
                    status='scheduled'
                )
                games.append(game)
                db.session.add(game)
            db.session.commit()
            
            total_wagered = 0
            for i, game in enumerate(games):
                wager_amount = 100.0 + (i * 50)
                bet_data = {
                    'team_picked': game.home_team,
                    'wager_amount': wager_amount
                }
                validator.validate_and_create_bet(bet_data, sample_user, game)
                total_wagered += wager_amount
            
            # Verify user statistics
            db.session.refresh(sample_user)
            assert sample_user.total_bets == initial_total_bets + 3
            assert sample_user.balance == initial_balance - total_wagered
            
            # Verify total matches individual transactions
            transactions = Transaction.query.filter_by(user_id=sample_user.id, type='bet_placed').all()
            transaction_total = sum(abs(t.amount) for t in transactions)
            assert transaction_total == total_wagered