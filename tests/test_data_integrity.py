"""
Tests for data integrity validation

Tests the enhanced win percentage calculation and data validation features
"""

import pytest
from app import create_app, db
from app.models import User


class TestDataIntegrity:
    """Test data integrity validation and fixes"""
    
    def test_win_percentage_with_consistent_data(self, app):
        """Test win percentage calculation with consistent bet counts"""
        with app.app_context():
            user = User(
                discord_id='test_consistent',
                username='ConsistentUser',
                total_bets=10,
                winning_bets=7,
                losing_bets=3  # 7 + 3 = 10 (consistent)
            )
            db.session.add(user)
            db.session.commit()
            
            # Should calculate normal win percentage
            assert user.win_percentage == 70.0
            assert user.validate_bet_counts() is True
    
    def test_win_percentage_with_inconsistent_data(self, app):
        """Test win percentage calculation handles inconsistent bet counts"""
        with app.app_context():
            user = User(
                discord_id='test_inconsistent',
                username='InconsistentUser',
                total_bets=5,  # This doesn't match winning + losing
                winning_bets=8,
                losing_bets=2  # 8 + 2 = 10, not 5
            )
            db.session.add(user)
            db.session.commit()
            
            # Should use actual total (8 + 2 = 10) for calculation
            # 8/10 = 80%
            assert user.win_percentage == 80.0
            assert user.validate_bet_counts() is False
    
    def test_win_percentage_caps_at_100_percent(self, app):
        """Test that win percentage is capped at 100%"""
        with app.app_context():
            user = User(
                discord_id='test_cap',
                username='CapUser',
                total_bets=5,
                winning_bets=5,
                losing_bets=0  # 100% win rate
            )
            db.session.add(user)
            db.session.commit()
            
            # Should be exactly 100%, not more
            assert user.win_percentage == 100.0
    
    def test_win_percentage_with_zero_bets(self, app):
        """Test win percentage with zero total bets"""
        with app.app_context():
            user = User(
                discord_id='test_zero',
                username='ZeroUser',
                total_bets=0,
                winning_bets=0,
                losing_bets=0
            )
            db.session.add(user)
            db.session.commit()
            
            # Should return 0% for users with no bets
            assert user.win_percentage == 0.0
    
    def test_bet_count_validation(self, app):
        """Test bet count validation methods"""
        with app.app_context():
            # Consistent data
            user1 = User(
                discord_id='test_valid',
                username='ValidUser',
                total_bets=10,
                winning_bets=6,
                losing_bets=4
            )
            assert user1.validate_bet_counts() is True
            
            # Inconsistent data
            user2 = User(
                discord_id='test_invalid',
                username='InvalidUser',
                total_bets=10,
                winning_bets=8,
                losing_bets=5  # 8 + 5 = 13, not 10
            )
            assert user2.validate_bet_counts() is False
    
    def test_fix_bet_counts_method(self, app):
        """Test the fix_bet_counts method"""
        with app.app_context():
            user = User(
                discord_id='test_fix',
                username='FixUser',
                total_bets=5,  # Wrong total
                winning_bets=7,
                losing_bets=3  # Should be 10 total
            )
            
            assert user.validate_bet_counts() is False
            
            # Fix the counts
            user.fix_bet_counts()
            
            # Now should be consistent
            assert user.total_bets == 10
            assert user.validate_bet_counts() is True
            assert user.win_percentage == 70.0
    
    def test_leaderboard_win_rates_are_valid(self, app):
        """Test that all leaderboard win rates are within 0-100% range"""
        with app.app_context():
            from app.routes.stats import get_leaderboard_rankings
            
            # Get all users by win rate
            rankings = get_leaderboard_rankings('win_rate', limit=100)
            
            for user_data in rankings:
                win_rate = user_data['win_percentage']
                # All win rates should be between 0 and 100
                assert 0.0 <= win_rate <= 100.0, f"User {user_data['username']} has invalid win rate: {win_rate}%"
    
    def test_win_percentage_precision(self, app):
        """Test win percentage calculation precision"""
        with app.app_context():
            user = User(
                discord_id='test_precision',
                username='PrecisionUser',
                total_bets=3,
                winning_bets=2,
                losing_bets=1
            )
            db.session.add(user)
            db.session.commit()
            
            # 2/3 = 0.6666... = 66.666...%
            expected = (2 / 3) * 100
            assert abs(user.win_percentage - expected) < 0.001  # Within small tolerance