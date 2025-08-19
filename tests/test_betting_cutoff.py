"""
Tests for 5-minute betting cutoff functionality

Tests the 5-minute betting cutoff including:
- Enhanced is_bettable property with 5-minute buffer
- Updated bet placement validation
- Bet cancellation time restrictions
- Edge cases for timing validation
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Game, Bet
from app.services.bet_service import BetValidator


class TestBettingCutoff:
    """Test suite for 5-minute betting cutoff feature"""
    
    @pytest.fixture
    def app(self):
        """Create application for testing"""
        app = create_app('testing')
        
        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def test_user(self, app):
        """Create test user"""
        with app.app_context():
            user = User(
                discord_id='123456789',
                username='TestUser',
                email='test@example.com',
                balance=1000.00,
                starting_balance=1000.00
            )
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            user_id = user.id
            discord_id = user.discord_id
            return {'id': user_id, 'discord_id': discord_id}
    
    def test_game_is_bettable_more_than_5_minutes_before(self, app):
        """Test that game is bettable when more than 5 minutes before start"""
        with app.app_context():
            # Game starts in 10 minutes
            game = Game(
                espn_game_id='future_game',
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow() + timedelta(minutes=10),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Game should be bettable
            assert game.is_bettable is True
    
    def test_game_is_not_bettable_within_5_minutes(self, app):
        """Test that game is not bettable when within 5 minutes of start"""
        with app.app_context():
            # Game starts in 3 minutes
            game = Game(
                espn_game_id='soon_game',
                home_team='Team C',
                away_team='Team D',
                game_time=datetime.utcnow() + timedelta(minutes=3),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Game should not be bettable
            assert game.is_bettable is False
    
    def test_game_is_not_bettable_exactly_5_minutes_before(self, app):
        """Test that game is not bettable exactly 5 minutes before start"""
        with app.app_context():
            # Game starts in exactly 5 minutes
            game = Game(
                espn_game_id='edge_game',
                home_team='Team E',
                away_team='Team F',
                game_time=datetime.utcnow() + timedelta(minutes=5),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Game should not be bettable (cutoff is exclusive)
            assert game.is_bettable is False
    
    def test_game_is_bettable_just_over_5_minutes_before(self, app):
        """Test that game is bettable just over 5 minutes before start"""
        with app.app_context():
            # Game starts in 5 minutes and 10 seconds
            game = Game(
                espn_game_id='edge_safe_game',
                home_team='Team G',
                away_team='Team H',
                game_time=datetime.utcnow() + timedelta(minutes=5, seconds=10),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Game should be bettable
            assert game.is_bettable is True
    
    def test_game_is_not_bettable_after_start(self, app):
        """Test that game is not bettable after it has started"""
        with app.app_context():
            # Game started 10 minutes ago
            game = Game(
                espn_game_id='past_game',
                home_team='Team I',
                away_team='Team J',
                game_time=datetime.utcnow() - timedelta(minutes=10),
                week=1,
                season=2025,
                status='in_progress'
            )
            db.session.add(game)
            db.session.commit()
            
            # Game should not be bettable
            assert game.is_bettable is False
    
    def test_game_is_not_bettable_with_wrong_status(self, app):
        """Test that game is not bettable with non-scheduled status"""
        with app.app_context():
            # Game is in the future but has wrong status
            game = Game(
                espn_game_id='wrong_status_game',
                home_team='Team K',
                away_team='Team L',
                game_time=datetime.utcnow() + timedelta(hours=2),
                week=1,
                season=2025,
                status='cancelled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Game should not be bettable
            assert game.is_bettable is False
    
    def test_bet_placement_validation_rejects_within_cutoff(self, app, test_user):
        """Test that bet placement validation rejects bets within 5-minute cutoff"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create game within cutoff window
            game = Game(
                espn_game_id='cutoff_game',
                home_team='Team M',
                away_team='Team N',
                game_time=datetime.utcnow() + timedelta(minutes=3),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Try to validate timing
            result = validator.validate_game_timing(game)
            
            assert result is False
            assert any("5 minutes" in error for error in validator.errors)
    
    def test_bet_placement_validation_allows_outside_cutoff(self, app, test_user):
        """Test that bet placement validation allows bets outside 5-minute cutoff"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create game outside cutoff window
            game = Game(
                espn_game_id='safe_game',
                home_team='Team O',
                away_team='Team P',
                game_time=datetime.utcnow() + timedelta(minutes=10),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Try to validate timing
            result = validator.validate_game_timing(game)
            
            assert result is True
            assert len(validator.errors) == 0
    
    def test_bet_cancellation_allowed_outside_cutoff(self, app, test_user):
        """Test that bet cancellation is allowed when outside 5-minute cutoff"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create game outside cutoff window
            game = Game(
                espn_game_id='cancel_safe_game',
                home_team='Team Q',
                away_team='Team R',
                game_time=datetime.utcnow() + timedelta(minutes=10),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Create a pending bet
            bet = Bet(
                user_id=user.id,
                game_id=game.id,
                team_picked=game.home_team,
                wager_amount=100.00,
                potential_payout=200.00,
                status='pending'
            )
            db.session.add(bet)
            db.session.commit()
            
            # Try to cancel the bet
            initial_balance = user.balance
            result = validator.cancel_bet(user, bet.id)
            
            assert result is True
            db.session.refresh(user)
            assert user.balance == initial_balance + 100.00
    
    def test_bet_cancellation_blocked_within_cutoff(self, app, test_user):
        """Test that bet cancellation is blocked when within 5-minute cutoff"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create game within cutoff window
            game = Game(
                espn_game_id='cancel_blocked_game',
                home_team='Team S',
                away_team='Team T',
                game_time=datetime.utcnow() + timedelta(minutes=3),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Create a pending bet
            bet = Bet(
                user_id=user.id,
                game_id=game.id,
                team_picked=game.home_team,
                wager_amount=100.00,
                potential_payout=200.00,
                status='pending'
            )
            db.session.add(bet)
            db.session.commit()
            
            # Try to cancel the bet
            initial_balance = user.balance
            result = validator.cancel_bet(user, bet.id)
            
            assert result is False
            assert any("5 minutes" in error for error in validator.errors)
            # Balance should remain unchanged
            db.session.refresh(user)
            assert user.balance == initial_balance
    
    def test_comprehensive_bet_validation_with_cutoff(self, app, test_user):
        """Test comprehensive bet validation includes 5-minute cutoff check"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create game within cutoff window
            game = Game(
                espn_game_id='comprehensive_game',
                home_team='Team U',
                away_team='Team V',
                game_time=datetime.utcnow() + timedelta(minutes=2),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Try comprehensive validation
            result = validator.validate_bet_comprehensive(
                user, game.id, game.home_team, 50.00
            )
            
            assert result is False
            assert any("5 minutes" in error for error in validator.errors)
    
    def test_edge_case_game_time_precision(self, app):
        """Test edge case with microsecond precision around 5-minute cutoff"""
        with app.app_context():
            # Game starts in exactly 5 minutes minus 1 microsecond
            cutoff_time = datetime.utcnow() + timedelta(minutes=5, microseconds=-1)
            game = Game(
                espn_game_id='precision_game',
                home_team='Team W',
                away_team='Team X',
                game_time=cutoff_time,
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Should not be bettable (within 5-minute window)
            assert game.is_bettable is False
    
    def test_multiple_games_cutoff_scenarios(self, app):
        """Test multiple games with different cutoff scenarios"""
        with app.app_context():
            now = datetime.utcnow()
            
            # Game 1: Way in future (bettable)
            game1 = Game(
                espn_game_id='future1',
                home_team='Future A',
                away_team='Future B',
                game_time=now + timedelta(hours=2),
                week=1,
                season=2025,
                status='scheduled'
            )
            
            # Game 2: Just outside cutoff (bettable)
            game2 = Game(
                espn_game_id='edge1',
                home_team='Edge A',
                away_team='Edge B',
                game_time=now + timedelta(minutes=6),
                week=1,
                season=2025,
                status='scheduled'
            )
            
            # Game 3: Just inside cutoff (not bettable)
            game3 = Game(
                espn_game_id='edge2',
                home_team='Edge C',
                away_team='Edge D',
                game_time=now + timedelta(minutes=4),
                week=1,
                season=2025,
                status='scheduled'
            )
            
            # Game 4: Already started (not bettable)
            game4 = Game(
                espn_game_id='past1',
                home_team='Past A',
                away_team='Past B',
                game_time=now - timedelta(minutes=10),
                week=1,
                season=2025,
                status='in_progress'
            )
            
            db.session.add_all([game1, game2, game3, game4])
            db.session.commit()
            
            # Verify each game's bettability
            assert game1.is_bettable is True
            assert game2.is_bettable is True
            assert game3.is_bettable is False
            assert game4.is_bettable is False
    
    def test_cutoff_validation_error_messages(self, app, test_user):
        """Test that cutoff validation provides clear error messages"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create game within cutoff
            game = Game(
                espn_game_id='error_test_game',
                home_team='Error A',
                away_team='Error B',
                game_time=datetime.utcnow() + timedelta(minutes=1),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Test bet placement validation error
            validator.validate_game_timing(game)
            
            # Should have clear, user-friendly error message
            assert len(validator.errors) > 0
            error_message = validator.errors[0]
            assert "5 minutes" in error_message
            assert "before" in error_message.lower()
            assert "start" in error_message.lower()