import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from app import create_app, db
from app.models import User, Game, Bet, Transaction
from flask import url_for


class TestBettingRoutes:
    """Test betting interface routes and functionality"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask application"""
        app = create_app('testing')
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def sample_user(self, app):
        """Create sample user for testing"""
        with app.app_context():
            user = User(
                discord_id='123456789',
                username='testuser',
                balance=5000.0,
                starting_balance=10000.0
            )
            db.session.add(user)
            db.session.commit()
            return user
    
    @pytest.fixture
    def sample_games(self, app):
        """Create sample games for testing"""
        with app.app_context():
            # Future game - bettable
            future_game = Game(
                espn_game_id='401547440',
                week=1,
                season=2024,
                home_team='Kansas City Chiefs',
                home_team_abbr='KC',
                away_team='Detroit Lions',
                away_team_abbr='DET',
                game_time=datetime.utcnow() + timedelta(days=1),
                status='scheduled'
            )
            
            # Past game - not bettable
            past_game = Game(
                espn_game_id='401547441',
                week=1,
                season=2024,
                home_team='Green Bay Packers',
                home_team_abbr='GB',
                away_team='Chicago Bears',
                away_team_abbr='CHI',
                game_time=datetime.utcnow() - timedelta(days=1),
                status='final',
                home_score=24,
                away_score=17,
                winner='Green Bay Packers'
            )
            
            # In progress game - not bettable
            active_game = Game(
                espn_game_id='401547442',
                week=2,
                season=2024,
                home_team='Buffalo Bills',
                home_team_abbr='BUF',
                away_team='Miami Dolphins',
                away_team_abbr='MIA',
                game_time=datetime.utcnow() - timedelta(hours=1),
                status='in_progress',
                quarter='Q3',
                time_remaining='8:45'
            )
            
            db.session.add_all([future_game, past_game, active_game])
            db.session.commit()
            return {
                'future': future_game,
                'past': past_game,
                'active': active_game
            }
    
    @pytest.fixture
    def authenticated_session(self, client, sample_user):
        """Create authenticated session"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = sample_user.discord_id
        return client

    def test_games_route_unauthenticated(self, client):
        """Test games route redirects when not authenticated"""
        response = client.get('/betting/games')
        assert response.status_code == 302  # Redirect to login
    
    def test_games_route_authenticated(self, authenticated_session, sample_games):
        """Test games route shows available games when authenticated"""
        response = authenticated_session.get('/betting/games')
        assert response.status_code == 200
        
        # Check that the page contains game information
        assert b'Kansas City Chiefs' in response.data
        assert b'Detroit Lions' in response.data
        assert b'Available Games' in response.data
    
    def test_games_route_week_filter(self, authenticated_session, sample_games):
        """Test games route with week filter"""
        response = authenticated_session.get('/betting/games?week=1')
        assert response.status_code == 200
        
        # Should show Week 1 games
        assert b'Kansas City Chiefs' in response.data
        assert b'Green Bay Packers' in response.data
        
        # Should not show Week 2 games
        assert b'Buffalo Bills' not in response.data
    
    def test_games_route_shows_betting_status(self, authenticated_session, sample_games):
        """Test games route shows correct betting status"""
        response = authenticated_session.get('/betting/games')
        assert response.status_code == 200
        
        # Future game should show "Betting Open"
        content = response.data.decode('utf-8')
        assert 'Betting Open' in content
        assert 'Betting Closed' in content
    
    def test_place_bet_route_unauthenticated(self, client, sample_games):
        """Test place bet route redirects when not authenticated"""
        response = client.get(f'/betting/place/{sample_games["future"].id}')
        assert response.status_code == 302  # Redirect to login
    
    def test_place_bet_route_get_bettable_game(self, authenticated_session, sample_games):
        """Test place bet route GET for bettable game"""
        response = authenticated_session.get(f'/betting/place/{sample_games["future"].id}')
        assert response.status_code == 200
        
        # Check that betting form is displayed
        assert b'Place Your Bet' in response.data
        assert b'Kansas City Chiefs' in response.data
        assert b'Detroit Lions' in response.data
        assert b'Which team will win?' in response.data
        assert b'Wager Amount' in response.data
    
    def test_place_bet_route_get_non_bettable_game(self, authenticated_session, sample_games):
        """Test place bet route GET for non-bettable game"""
        response = authenticated_session.get(f'/betting/place/{sample_games["past"].id}')
        assert response.status_code == 200
        
        # Should show betting closed message
        assert b'Betting Closed' in response.data
        assert b'Place Your Bet' not in response.data
    
    def test_place_bet_route_nonexistent_game(self, authenticated_session):
        """Test place bet route with nonexistent game ID"""
        response = authenticated_session.get('/betting/place/99999')
        assert response.status_code == 404
    
    def test_place_bet_post_valid_bet(self, authenticated_session, sample_user, sample_games):
        """Test placing a valid bet"""
        game = sample_games['future']
        
        response = authenticated_session.post(f'/betting/place/{game.id}', data={
            'team_picked': 'Kansas City Chiefs',
            'wager_amount': '100.00'
        })
        
        # Should redirect to view bet page
        assert response.status_code == 302
        
        # Verify bet was created
        with authenticated_session.application.app_context():
            bet = Bet.query.filter_by(user_id=sample_user.id, game_id=game.id).first()
            assert bet is not None
            assert bet.team_picked == 'Kansas City Chiefs'
            assert bet.wager_amount == 100.0
            assert bet.potential_payout == 200.0
            assert bet.status == 'pending'
            
            # Verify user balance was updated
            updated_user = User.query.get(sample_user.id)
            assert updated_user.balance == 4900.0  # 5000 - 100
            assert updated_user.total_bets == 1
            
            # Verify game statistics were updated
            updated_game = Game.query.get(game.id)
            assert updated_game.total_bets == 1
            assert updated_game.total_wagered == 100.0
            assert updated_game.home_bets == 1
            assert updated_game.away_bets == 0
            
            # Verify transaction was created
            transaction = Transaction.query.filter_by(user_id=sample_user.id).first()
            assert transaction is not None
            assert transaction.type == 'bet_placed'
            assert transaction.amount == -100.0
    
    def test_place_bet_post_invalid_team(self, authenticated_session, sample_games):
        """Test placing bet with invalid team selection"""
        game = sample_games['future']
        
        response = authenticated_session.post(f'/betting/place/{game.id}', data={
            'team_picked': 'Invalid Team',
            'wager_amount': '100.00'
        })
        
        # Should stay on same page with error
        assert response.status_code == 200
        assert b'Invalid team selection' in response.data
    
    def test_place_bet_post_insufficient_balance(self, authenticated_session, sample_games):
        """Test placing bet with insufficient balance"""
        game = sample_games['future']
        
        response = authenticated_session.post(f'/betting/place/{game.id}', data={
            'team_picked': 'Kansas City Chiefs',
            'wager_amount': '10000.00'  # More than user's balance
        })
        
        # Should stay on same page with error
        assert response.status_code == 200
        assert b'Insufficient balance' in response.data
    
    def test_place_bet_post_invalid_amount(self, authenticated_session, sample_games):
        """Test placing bet with invalid wager amount"""
        game = sample_games['future']
        
        # Test zero amount
        response = authenticated_session.post(f'/betting/place/{game.id}', data={
            'team_picked': 'Kansas City Chiefs',
            'wager_amount': '0'
        })
        
        assert response.status_code == 200
        assert b'Wager amount must be greater than 0' in response.data
        
        # Test negative amount
        response = authenticated_session.post(f'/betting/place/{game.id}', data={
            'team_picked': 'Kansas City Chiefs',
            'wager_amount': '-50'
        })
        
        assert response.status_code == 200
        assert b'Wager amount must be greater than 0' in response.data
    
    def test_place_bet_duplicate_bet(self, authenticated_session, sample_user, sample_games):
        """Test placing duplicate bet on same game"""
        game = sample_games['future']
        
        # Place first bet
        with authenticated_session.application.app_context():
            bet = Bet(
                user_id=sample_user.id,
                game_id=game.id,
                team_picked='Kansas City Chiefs',
                wager_amount=100.0,
                potential_payout=200.0
            )
            db.session.add(bet)
            db.session.commit()
            bet_id = bet.id
        
        # Try to place second bet
        response = authenticated_session.get(f'/betting/place/{game.id}')
        assert response.status_code == 302  # Should redirect to existing bet
        
        # Should redirect to view bet page
        assert f'/betting/bet/{bet_id}' in response.location
    
    def test_view_bet_route_unauthenticated(self, client):
        """Test view bet route redirects when not authenticated"""
        response = client.get('/betting/bet/1')
        assert response.status_code == 302  # Redirect to login
    
    def test_view_bet_route_valid_bet(self, authenticated_session, sample_user, sample_games):
        """Test viewing a valid bet"""
        game = sample_games['future']
        
        with authenticated_session.application.app_context():
            bet = Bet(
                user_id=sample_user.id,
                game_id=game.id,
                team_picked='Kansas City Chiefs',
                wager_amount=100.0,
                potential_payout=200.0
            )
            db.session.add(bet)
            db.session.commit()
            bet_id = bet.id
        
        response = authenticated_session.get(f'/betting/bet/{bet_id}')
        assert response.status_code == 200
        
        # Check bet details are displayed
        assert b'Kansas City Chiefs' in response.data
        assert b'$100.00' in response.data
        assert b'$200.00' in response.data
        assert b'Pending' in response.data
    
    def test_view_bet_route_other_user_bet(self, authenticated_session, sample_games):
        """Test viewing another user's bet"""
        with authenticated_session.application.app_context():
            # Create another user
            other_user = User(discord_id='987654321', username='otheruser')
            db.session.add(other_user)
            db.session.commit()
            
            # Create bet for other user
            bet = Bet(
                user_id=other_user.id,
                game_id=sample_games['future'].id,
                team_picked='Kansas City Chiefs',
                wager_amount=100.0,
                potential_payout=200.0
            )
            db.session.add(bet)
            db.session.commit()
            bet_id = bet.id
        
        response = authenticated_session.get(f'/betting/bet/{bet_id}')
        assert response.status_code == 302  # Should redirect to dashboard
    
    def test_view_bet_route_nonexistent_bet(self, authenticated_session):
        """Test viewing nonexistent bet"""
        response = authenticated_session.get('/betting/bet/99999')
        assert response.status_code == 404
    
    def test_betting_history_route_unauthenticated(self, client):
        """Test betting history route redirects when not authenticated"""
        response = client.get('/betting/history')
        assert response.status_code == 302  # Redirect to login
    
    def test_betting_history_route_no_bets(self, authenticated_session):
        """Test betting history with no bets"""
        response = authenticated_session.get('/betting/history')
        assert response.status_code == 200
        
        # Should show "no bets" message
        assert b'No Betting History' in response.data
        assert b'Place Your First Bet' in response.data
    
    def test_betting_history_route_with_bets(self, authenticated_session, sample_user, sample_games):
        """Test betting history with existing bets"""
        with authenticated_session.application.app_context():
            # Create multiple bets with different statuses
            bet1 = Bet(
                user_id=sample_user.id,
                game_id=sample_games['future'].id,
                team_picked='Kansas City Chiefs',
                wager_amount=100.0,
                potential_payout=200.0,
                status='pending'
            )
            
            bet2 = Bet(
                user_id=sample_user.id,
                game_id=sample_games['past'].id,
                team_picked='Green Bay Packers',
                wager_amount=50.0,
                potential_payout=100.0,
                actual_payout=100.0,
                status='won'
            )
            
            db.session.add_all([bet1, bet2])
            db.session.commit()
        
        response = authenticated_session.get('/betting/history')
        assert response.status_code == 200
        
        # Should show both bets
        assert b'Kansas City Chiefs' in response.data
        assert b'Green Bay Packers' in response.data
        assert b'$100.00' in response.data
        assert b'$50.00' in response.data
    
    def test_betting_history_status_filter(self, authenticated_session, sample_user, sample_games):
        """Test betting history status filter"""
        with authenticated_session.application.app_context():
            # Create bets with different statuses
            pending_bet = Bet(
                user_id=sample_user.id,
                game_id=sample_games['future'].id,
                team_picked='Kansas City Chiefs',
                wager_amount=100.0,
                status='pending'
            )
            
            won_bet = Bet(
                user_id=sample_user.id,
                game_id=sample_games['past'].id,
                team_picked='Green Bay Packers',
                wager_amount=50.0,
                status='won'
            )
            
            db.session.add_all([pending_bet, won_bet])
            db.session.commit()
        
        # Test pending filter
        response = authenticated_session.get('/betting/history?status=pending')
        assert response.status_code == 200
        assert b'Kansas City Chiefs' in response.data
        assert b'Green Bay Packers' not in response.data
        
        # Test won filter
        response = authenticated_session.get('/betting/history?status=won')
        assert response.status_code == 200
        assert b'Green Bay Packers' in response.data
        assert b'Kansas City Chiefs' not in response.data
    
    def test_betting_history_pagination(self, authenticated_session, sample_user, sample_games):
        """Test betting history pagination"""
        with authenticated_session.application.app_context():
            # Create many bets to test pagination
            bets = []
            for i in range(25):  # More than default page size
                bet = Bet(
                    user_id=sample_user.id,
                    game_id=sample_games['future'].id,
                    team_picked='Kansas City Chiefs',
                    wager_amount=10.0 + i,
                    status='pending'
                )
                bets.append(bet)
            
            db.session.add_all(bets)
            db.session.commit()
        
        # Test first page
        response = authenticated_session.get('/betting/history')
        assert response.status_code == 200
        assert b'Kansas City Chiefs' in response.data
        
        # Should have pagination controls for many bets
        # Note: This would need actual pagination implementation in the route
        
    def test_place_bet_away_team_selection(self, authenticated_session, sample_user, sample_games):
        """Test placing bet on away team"""
        game = sample_games['future']
        
        response = authenticated_session.post(f'/betting/place/{game.id}', data={
            'team_picked': 'Detroit Lions',  # Away team
            'wager_amount': '100.00'
        })
        
        # Should redirect to view bet page
        assert response.status_code == 302
        
        # Verify bet was created for away team
        with authenticated_session.application.app_context():
            bet = Bet.query.filter_by(user_id=sample_user.id, game_id=game.id).first()
            assert bet.team_picked == 'Detroit Lions'
            
            # Verify game statistics were updated for away team
            updated_game = Game.query.get(game.id)
            assert updated_game.away_bets == 1
            assert updated_game.home_bets == 0