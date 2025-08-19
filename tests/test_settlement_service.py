"""
Tests for automated bet settlement service

Tests the core settlement logic including:
- Payout calculation for wins, losses, and ties
- Balance updates for users
- Bet status changes
- Integration with scheduler for automated settlement
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app import create_app, db
from app.models import User, Game, Bet, Transaction
from app.services.settlement_service import SettlementService


@pytest.fixture
def settlement_service():
    """Create settlement service instance for testing"""
    return SettlementService()


@pytest.fixture
def sample_user(app):
    """Create sample user for testing"""
    with app.app_context():
        user = User(
            discord_id='test_user_123',
            username='TestUser',
            balance=10000.0,
            starting_balance=10000.0
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def sample_game(app):
    """Create sample completed game for testing"""
    with app.app_context():
        game = Game(
            espn_game_id='401671001',
            home_team='Miami Dolphins',
            away_team='Buffalo Bills',
            home_team_abbr='MIA',
            away_team_abbr='BUF',
            home_score=21,
            away_score=17,
            game_time=datetime.utcnow() - timedelta(hours=3),
            status='final',
            winner='Miami Dolphins',
            is_tie=False,
            week=1,
            season=2024
        )
        db.session.add(game)
        db.session.commit()
        return game


@pytest.fixture
def tie_game(app):
    """Create sample tie game for testing"""
    with app.app_context():
        game = Game(
            espn_game_id='401671002',
            home_team='New York Jets',
            away_team='New England Patriots',
            home_team_abbr='NYJ',
            away_team_abbr='NE',
            home_score=14,
            away_score=14,
            game_time=datetime.utcnow() - timedelta(hours=3),
            status='final',
            winner=None,
            is_tie=True,
            week=1,
            season=2024
        )
        db.session.add(game)
        db.session.commit()
        return game


@pytest.fixture
def pending_bet_winning(app):
    """Create pending bet that should win - returns bet ID"""
    with app.app_context():
        # Create user directly in this context
        user = User(
            discord_id='test_user_123',
            username='TestUser',
            balance=10000.0,
            starting_balance=10000.0
        )
        db.session.add(user)
        
        # Create game directly in this context
        game = Game(
            espn_game_id='401671001',
            home_team='Miami Dolphins',
            away_team='Buffalo Bills',
            home_team_abbr='MIA',
            away_team_abbr='BUF',
            home_score=21,
            away_score=17,
            game_time=datetime.utcnow() - timedelta(hours=3),
            status='final',
            winner='Miami Dolphins',
            is_tie=False,
            week=1,
            season=2024
        )
        db.session.add(game)
        db.session.flush()  # Get IDs
        
        bet = Bet(
            user_id=user.id,
            game_id=game.id,
            team_picked='Miami Dolphins',  # Winner
            wager_amount=100.0,
            potential_payout=200.0,
            status='pending'
        )
        db.session.add(bet)
        db.session.commit()
        return bet.id


@pytest.fixture
def pending_bet_losing(app):
    """Create pending bet that should lose - returns bet ID"""
    with app.app_context():
        # Create user directly in this context
        user = User(
            discord_id='test_user_124',
            username='TestUser2',
            balance=10000.0,
            starting_balance=10000.0
        )
        db.session.add(user)
        
        # Create game directly in this context
        game = Game(
            espn_game_id='401671003',
            home_team='Miami Dolphins',
            away_team='Buffalo Bills',
            home_team_abbr='MIA',
            away_team_abbr='BUF',
            home_score=21,
            away_score=17,
            game_time=datetime.utcnow() - timedelta(hours=3),
            status='final',
            winner='Miami Dolphins',
            is_tie=False,
            week=1,
            season=2024
        )
        db.session.add(game)
        db.session.flush()  # Get IDs
        
        bet = Bet(
            user_id=user.id,
            game_id=game.id,
            team_picked='Buffalo Bills',  # Loser
            wager_amount=50.0,
            potential_payout=100.0,
            status='pending'
        )
        db.session.add(bet)
        db.session.commit()
        return bet.id


@pytest.fixture
def pending_bet_tie(app):
    """Create pending bet on tie game - returns bet ID"""
    with app.app_context():
        # Create user directly in this context
        user = User(
            discord_id='test_user_125',
            username='TestUser3',
            balance=10000.0,
            starting_balance=10000.0
        )
        db.session.add(user)
        
        # Create tie game directly in this context
        game = Game(
            espn_game_id='401671004',
            home_team='New York Jets',
            away_team='New England Patriots',
            home_team_abbr='NYJ',
            away_team_abbr='NE',
            home_score=14,
            away_score=14,
            game_time=datetime.utcnow() - timedelta(hours=3),
            status='final',
            winner=None,
            is_tie=True,
            week=1,
            season=2024
        )
        db.session.add(game)
        db.session.flush()  # Get IDs
        
        bet = Bet(
            user_id=user.id,
            game_id=game.id,
            team_picked='New York Jets',
            wager_amount=75.0,
            potential_payout=150.0,
            status='pending'
        )
        db.session.add(bet)
        db.session.commit()
        return bet.id


class TestSettlementService:
    """Test settlement service functionality"""
    
    def test_settle_winning_bet(self, app, settlement_service, pending_bet_winning):
        """Test settling a winning bet"""
        with app.app_context():
            # Get user from bet using the ID
            bet = Bet.query.get(pending_bet_winning)
            user = User.query.get(bet.user_id)
            initial_balance = user.balance
            
            # Settle the bet
            result = settlement_service.settle_bet(bet.id)
            
            # Refresh objects from database
            db.session.refresh(user)
            db.session.refresh(bet)
            
            # Verify settlement result
            assert result['success'] is True
            assert result['bet_id'] == bet.id
            assert result['status'] == 'won'
            assert result['payout'] == 200.0
            
            # Verify bet status
            assert bet.status == 'won'
            assert bet.actual_payout == 200.0
            assert bet.settled_at is not None
            
            # Verify user balance updated
            assert user.balance == initial_balance + 200.0
            assert user.winning_bets == 1
            assert user.total_winnings == 200.0
            
            # Verify transaction created
            transaction = Transaction.query.filter_by(
                user_id=user.id,
                bet_id=bet.id,
                type='bet_won'
            ).first()
            assert transaction is not None
            assert transaction.amount == 200.0
    
    def test_settle_losing_bet(self, app, settlement_service, pending_bet_losing):
        """Test settling a losing bet"""
        with app.app_context():
            # Get user from bet using the ID
            bet = Bet.query.get(pending_bet_losing)
            user = User.query.get(bet.user_id)
            initial_balance = user.balance
            
            # Settle the bet
            result = settlement_service.settle_bet(bet.id)
            
            # Refresh objects from database
            db.session.refresh(user)
            db.session.refresh(bet)
            
            # Verify settlement result
            assert result['success'] is True
            assert result['bet_id'] == bet.id
            assert result['status'] == 'lost'
            assert result['payout'] == 0.0
            
            # Verify bet status
            assert bet.status == 'lost'
            assert bet.actual_payout == 0.0
            assert bet.settled_at is not None
            
            # Verify user balance unchanged (already deducted when bet placed)
            assert user.balance == initial_balance
            assert user.losing_bets == 1
            assert user.total_losses == 50.0
            
            # Verify transaction created
            transaction = Transaction.query.filter_by(
                user_id=user.id,
                bet_id=bet.id,
                type='bet_lost'
            ).first()
            assert transaction is not None
            assert transaction.amount == 0.0
    
    def test_settle_tie_bet(self, app, settlement_service, pending_bet_tie):
        """Test settling a bet on tie game (push)"""
        with app.app_context():
            # Get user from bet using the ID
            bet = Bet.query.get(pending_bet_tie)
            user = User.query.get(bet.user_id)
            initial_balance = user.balance
            
            # Settle the bet
            result = settlement_service.settle_bet(bet.id)
            
            # Refresh objects from database
            db.session.refresh(user)
            db.session.refresh(bet)
            
            # Verify settlement result
            assert result['success'] is True
            assert result['bet_id'] == bet.id
            assert result['status'] == 'push'
            assert result['payout'] == 75.0  # Original wager returned
            
            # Verify bet status
            assert bet.status == 'push'
            assert bet.actual_payout == 75.0
            assert bet.settled_at is not None
            
            # Verify user balance - original wager returned
            assert user.balance == initial_balance + 75.0
            assert user.winning_bets == 0
            assert user.losing_bets == 0
            
            # Verify transaction created
            transaction = Transaction.query.filter_by(
                user_id=user.id,
                bet_id=bet.id,
                type='bet_push'
            ).first()
            assert transaction is not None
            assert transaction.amount == 75.0
    
    def test_settle_already_settled_bet(self, app, settlement_service, pending_bet_winning):
        """Test settling a bet that's already been settled"""
        with app.app_context():
            # First settlement
            settlement_service.settle_bet(pending_bet_winning)
            
            # Attempt second settlement
            result = settlement_service.settle_bet(pending_bet_winning)
            
            # Should return error
            assert result['success'] is False
            assert 'already settled' in result['error'].lower()
    
    def test_settle_bet_game_not_final(self, app, settlement_service):
        """Test settling bet when game is not final"""
        with app.app_context():
            # Create user
            user = User(
                discord_id='test_user_126',
                username='TestUser4',
                balance=10000.0,
                starting_balance=10000.0
            )
            db.session.add(user)
            
            # Create game that's not final
            game = Game(
                espn_game_id='401671005',
                home_team='Miami Dolphins',
                away_team='Buffalo Bills',
                home_team_abbr='MIA',
                away_team_abbr='BUF',
                home_score=14,
                away_score=10,
                game_time=datetime.utcnow() + timedelta(hours=1),
                status='in_progress',
                winner=None,
                is_tie=False,
                week=1,
                season=2024
            )
            db.session.add(game)
            db.session.flush()
            
            bet = Bet(
                user_id=user.id,
                game_id=game.id,
                team_picked='Miami Dolphins',
                wager_amount=100.0,
                potential_payout=200.0,
                status='pending'
            )
            db.session.add(bet)
            db.session.commit()
            
            # Attempt to settle
            result = settlement_service.settle_bet(bet.id)
            
            # Should return error
            assert result['success'] is False
            assert 'not final' in result['error'].lower()
    
    def test_settle_games_by_completion(self, app, settlement_service):
        """Test settling all bets for completed games"""
        with app.app_context():
            # Create user
            user = User(
                discord_id='test_user_127',
                username='TestUser5',
                balance=10000.0,
                starting_balance=10000.0
            )
            db.session.add(user)
            
            # Create completed game
            game = Game(
                espn_game_id='401671006',
                home_team='Miami Dolphins',
                away_team='Buffalo Bills',
                home_team_abbr='MIA',
                away_team_abbr='BUF',
                home_score=21,
                away_score=17,
                game_time=datetime.utcnow() - timedelta(hours=3),
                status='final',
                winner='Miami Dolphins',
                is_tie=False,
                week=1,
                season=2024
            )
            db.session.add(game)
            db.session.flush()
            
            # Create multiple bets on the completed game
            bets = []
            for i in range(3):
                bet = Bet(
                    user_id=user.id,
                    game_id=game.id,
                    team_picked='Miami Dolphins' if i % 2 == 0 else 'Buffalo Bills',
                    wager_amount=100.0,
                    potential_payout=200.0,
                    status='pending'
                )
                db.session.add(bet)
                bets.append(bet)
            db.session.commit()
            
            # Settle all completed games
            result = settlement_service.settle_completed_games()
            
            # Verify all bets were processed
            assert result['success'] is True
            assert result['games_processed'] == 1
            assert result['bets_settled'] == 3
            
            # Verify all bets are settled
            for bet in bets:
                db.session.refresh(bet)
                assert bet.status in ['won', 'lost']
                assert bet.settled_at is not None
    
    def test_settle_completed_games_no_bets(self, app, settlement_service):
        """Test settling completed games when no pending bets exist"""
        with app.app_context():
            # Create completed game with no bets
            game = Game(
                espn_game_id='401671007',
                home_team='Green Bay Packers',
                away_team='Chicago Bears',
                home_team_abbr='GB',
                away_team_abbr='CHI',
                home_score=28,
                away_score=14,
                game_time=datetime.utcnow() - timedelta(hours=3),
                status='final',
                winner='Green Bay Packers',
                is_tie=False,
                week=1,
                season=2024
            )
            db.session.add(game)
            db.session.commit()
            
            result = settlement_service.settle_completed_games()
            
            assert result['success'] is True
            assert result['games_processed'] == 1
            assert result['bets_settled'] == 0
    
    def test_settlement_database_rollback_on_error(self, app, settlement_service, pending_bet_winning):
        """Test that database changes rollback on error during settlement"""
        with app.app_context():
            bet = Bet.query.get(pending_bet_winning)
            user = User.query.get(bet.user_id)
            initial_balance = user.balance
            
            # Mock database commit to raise exception
            with patch.object(db.session, 'commit', side_effect=Exception('Database error')):
                result = settlement_service.settle_bet(bet.id)
                
                # Settlement should fail
                assert result['success'] is False
                assert 'Database error' in result['error']
                
                # User balance should be unchanged
                db.session.refresh(user)
                assert user.balance == initial_balance
                
                # Bet should still be pending
                db.session.refresh(bet)
                assert bet.status == 'pending'
    
    def test_integration_with_scheduler(self, app, settlement_service):
        """Test integration of settlement service with scheduler"""
        with app.app_context():
            # Mock scheduler
            mock_scheduler = MagicMock()
            
            # Add settlement job
            settlement_service.add_settlement_job(mock_scheduler, 'settlement_job', 30)
            
            # Verify job was added
            mock_scheduler.add_job.assert_called_once()
            args, kwargs = mock_scheduler.add_job.call_args
            
            assert kwargs['id'] == 'settlement_job'
            assert kwargs['trigger'] == 'interval'
            assert kwargs['minutes'] == 30
            # Check that the function argument exists and is callable
            assert len(args) > 0
            assert callable(args[0])