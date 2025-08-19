"""
Tests for bet cancellation functionality

Tests the ability to cancel pending bets including:
- Cancellation validation 
- Balance refund logic
- Transaction integrity
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Game, Bet
from app.services.bet_service import BetValidator


class TestBetCancellation:
    """Test suite for bet cancellation feature"""
    
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
            # Refresh to ensure we have the ID
            db.session.refresh(user)
            user_id = user.id
            discord_id = user.discord_id
            balance = user.balance
            # Return a dict with necessary data to avoid session issues
            return {'id': user_id, 'discord_id': discord_id, 'balance': balance}
    
    @pytest.fixture
    def future_game(self, app):
        """Create future game for betting"""
        with app.app_context():
            game = Game(
                espn_game_id='future_game',
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow() + timedelta(hours=2),
                week=1,
                season=2025,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            db.session.refresh(game)
            return {'id': game.id, 'home_team': game.home_team, 'away_team': game.away_team}
    
    @pytest.fixture
    def past_game(self, app):
        """Create past game (should not be cancellable)"""
        with app.app_context():
            game = Game(
                espn_game_id='past_game',
                home_team='Team C',
                away_team='Team D',
                game_time=datetime.utcnow() - timedelta(hours=1),
                week=1,
                season=2025,
                status='final',
                home_score=21,
                away_score=14
            )
            db.session.add(game)
            db.session.commit()
            db.session.refresh(game)
            return {'id': game.id, 'home_team': game.home_team}
    
    @pytest.fixture
    def pending_bet(self, app, test_user, future_game):
        """Create a pending bet for testing"""
        with app.app_context():
            bet = Bet(
                user_id=test_user['id'],
                game_id=future_game['id'],
                team_picked=future_game['home_team'],
                wager_amount=100.00,
                potential_payout=200.00,
                status='pending'
            )
            db.session.add(bet)
            db.session.commit()
            db.session.refresh(bet)
            return {'id': bet.id, 'wager_amount': bet.wager_amount}
    
    @pytest.fixture
    def settled_bet(self, app, test_user, past_game):
        """Create a settled bet (should not be cancellable)"""
        with app.app_context():
            bet = Bet(
                user_id=test_user['id'],
                game_id=past_game['id'],
                team_picked=past_game['home_team'],
                wager_amount=50.00,
                potential_payout=100.00,
                status='won',
                actual_payout=100.00,
                settled_at=datetime.utcnow()
            )
            db.session.add(bet)
            db.session.commit()
            db.session.refresh(bet)
            return {'id': bet.id}

    def test_cancel_pending_bet_success(self, app, test_user, pending_bet):
        """Test successful cancellation of a pending bet"""
        with app.app_context():
            validator = BetValidator()
            
            # Get user and bet objects
            user = db.session.get(User, test_user['id'])
            bet = db.session.get(Bet, pending_bet['id'])
            
            # Record initial balance
            initial_balance = user.balance
            wager_amount = bet.wager_amount
            
            # Cancel the bet
            result = validator.cancel_bet(user, bet.id)
            
            # Assert cancellation succeeded
            assert result is True
            assert len(validator.errors) == 0
            
            # Refresh objects
            db.session.refresh(user)
            db.session.refresh(bet)
            
            # Assert bet status changed
            assert bet.status == 'cancelled'
            assert bet.settled_at is not None
            
            # Assert balance refunded
            assert user.balance == initial_balance + wager_amount
    
    def test_cancel_nonexistent_bet(self, app, test_user):
        """Test cancelling a bet that doesn't exist"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            result = validator.cancel_bet(user, 99999)  # Non-existent bet ID
            
            assert result is False
            assert "Bet not found or not owned by user" in validator.errors
    
    def test_cancel_bet_wrong_user(self, app, pending_bet):
        """Test cancelling a bet by wrong user"""
        with app.app_context():
            validator = BetValidator()
            
            # Create different user
            other_user = User(
                discord_id='987654321',
                username='OtherUser',
                email='other@example.com',
                balance=500.00,
                starting_balance=500.00
            )
            db.session.add(other_user)
            db.session.commit()
            
            result = validator.cancel_bet(other_user, pending_bet['id'])
            
            assert result is False
            assert "Bet not found or not owned by user" in validator.errors
    
    def test_cancel_already_settled_bet(self, app, test_user, settled_bet):
        """Test cancelling a bet that's already settled"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            result = validator.cancel_bet(user, settled_bet['id'])
            
            assert result is False
            assert "Only pending bets can be cancelled" in validator.errors
    
    def test_cancel_bet_transaction_integrity(self, app, test_user, future_game):
        """Test that bet cancellation maintains transaction integrity"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create bet
            bet = Bet(
                user_id=user.id,
                game_id=future_game['id'],
                team_picked=future_game['home_team'],
                wager_amount=100.00,
                potential_payout=200.00,
                status='pending'
            )
            db.session.add(bet)
            db.session.commit()
            
            initial_balance = user.balance
            wager_amount = bet.wager_amount
            
            # Cancel bet
            result = validator.cancel_bet(user, bet.id)
            
            assert result is True
            
            # Verify atomic transaction completed
            db.session.refresh(user)
            db.session.refresh(bet)
            
            # Both bet status and balance should be updated atomically
            assert bet.status == 'cancelled'
            assert user.balance == initial_balance + wager_amount
    
    def test_multiple_bet_cancellations(self, app, test_user, future_game):
        """Test cancelling multiple bets maintains correct balances"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create multiple bets
            bets = []
            for i in range(3):
                bet = Bet(
                    user_id=user.id,
                    game_id=future_game['id'],
                    team_picked=future_game['home_team'] if i % 2 == 0 else future_game['away_team'],
                    wager_amount=50.00 * (i + 1),  # $50, $100, $150
                    potential_payout=100.00 * (i + 1),
                    status='pending'
                )
                db.session.add(bet)
                bets.append(bet)
            
            db.session.commit()
            
            initial_balance = user.balance
            total_wagers = sum(bet.wager_amount for bet in bets)
            
            # Cancel all bets
            for bet in bets:
                result = validator.cancel_bet(user, bet.id)
                assert result is True
            
            # Verify final balance
            db.session.refresh(user)
            assert user.balance == initial_balance + total_wagers
    
    def test_cancel_bet_validation_errors_cleared(self, app, test_user, pending_bet):
        """Test that validation errors are cleared between cancellation attempts"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # First attempt - cancel non-existent bet
            result1 = validator.cancel_bet(user, 99999)
            assert result1 is False
            assert len(validator.errors) > 0
            
            # Second attempt - cancel valid bet
            result2 = validator.cancel_bet(user, pending_bet['id'])
            assert result2 is True
            assert len(validator.errors) == 0  # Errors should be cleared
    
    def test_cancel_bet_updates_user_stats(self, app, test_user, pending_bet):
        """Test that bet cancellation doesn't affect user win/loss stats"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            initial_total_bets = user.total_bets
            initial_winning_bets = user.winning_bets
            initial_losing_bets = user.losing_bets
            
            # Cancel bet
            result = validator.cancel_bet(user, pending_bet['id'])
            assert result is True
            
            db.session.refresh(user)
            
            # Stats should remain unchanged - cancelled bets don't count
            assert user.total_bets == initial_total_bets
            assert user.winning_bets == initial_winning_bets
            assert user.losing_bets == initial_losing_bets
    
    def test_cancel_bet_with_insufficient_refund_amount(self, app, test_user, future_game):
        """Test edge case where user somehow has negative balance"""
        with app.app_context():
            validator = BetValidator()
            user = db.session.get(User, test_user['id'])
            
            # Create bet normally
            bet = Bet(
                user_id=user.id,
                game_id=future_game['id'],
                team_picked=future_game['home_team'],
                wager_amount=100.00,
                potential_payout=200.00,
                status='pending'
            )
            db.session.add(bet)
            db.session.commit()
            
            # Manually set user balance to negative (edge case)
            user.balance = -50.00
            db.session.commit()
            
            # Cancel bet should still work and bring balance closer to positive
            result = validator.cancel_bet(user, bet.id)
            assert result is True
            
            db.session.refresh(user)
            assert user.balance == 50.00  # -50 + 100 refund