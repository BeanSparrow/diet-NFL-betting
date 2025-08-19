"""
Tests for community leaderboard functionality

Tests the leaderboard features including:
- Balance rankings
- Win percentage calculations
- Leaderboard UI and sorting
- Real-time ranking updates
"""

import pytest
from datetime import datetime, timedelta
from flask import url_for

from app import create_app, db
from app.models import User, Game, Bet
from app.routes.stats import get_leaderboard_rankings


@pytest.fixture
def leaderboard_test_users(app):
    """Create test users with varying stats for leaderboard testing"""
    with app.app_context():
        users = []
        
        # User 1: High balance, good win rate
        user1 = User(
            discord_id='lead_user_1',
            username='TopPlayer',
            balance=15000.0,
            starting_balance=10000.0,
            total_bets=20,
            winning_bets=15,
            losing_bets=5,
            total_winnings=8000.0,
            total_losses=3000.0
        )
        db.session.add(user1)
        users.append(user1)
        
        # User 2: Medium balance, excellent win rate
        user2 = User(
            discord_id='lead_user_2',
            username='WinStreak',
            balance=12000.0,
            starting_balance=10000.0,
            total_bets=10,
            winning_bets=9,
            losing_bets=1,
            total_winnings=3000.0,
            total_losses=1000.0
        )
        db.session.add(user2)
        users.append(user2)
        
        # User 3: Lower balance, poor win rate
        user3 = User(
            discord_id='lead_user_3',
            username='Unlucky',
            balance=8000.0,
            starting_balance=10000.0,
            total_bets=15,
            winning_bets=3,
            losing_bets=12,
            total_winnings=1500.0,
            total_losses=3500.0
        )
        db.session.add(user3)
        users.append(user3)
        
        # User 4: No bets yet
        user4 = User(
            discord_id='lead_user_4',
            username='NewPlayer',
            balance=10000.0,
            starting_balance=10000.0,
            total_bets=0,
            winning_bets=0,
            losing_bets=0,
            total_winnings=0.0,
            total_losses=0.0
        )
        db.session.add(user4)
        users.append(user4)
        
        db.session.commit()
        return users


class TestLeaderboardRankings:
    """Test leaderboard ranking logic"""
    
    def test_balance_ranking(self, app, leaderboard_test_users):
        """Test ranking by balance"""
        with app.app_context():
            rankings = get_leaderboard_rankings('balance', limit=10)
            
            # Should be ordered by balance descending
            assert len(rankings) == 4
            assert rankings[0]['rank'] == 1
            assert rankings[0]['username'] == 'TopPlayer'
            assert rankings[0]['balance'] == 15000.0
            
            assert rankings[1]['username'] == 'WinStreak'
            assert rankings[1]['balance'] == 12000.0
            
            assert rankings[2]['username'] == 'NewPlayer'
            assert rankings[2]['balance'] == 10000.0
            
            assert rankings[3]['username'] == 'Unlucky'
            assert rankings[3]['balance'] == 8000.0
    
    def test_profit_ranking(self, app, leaderboard_test_users):
        """Test ranking by profit/loss"""
        with app.app_context():
            rankings = get_leaderboard_rankings('profit', limit=10)
            
            # Should be ordered by profit descending
            assert len(rankings) == 4
            assert rankings[0]['username'] == 'TopPlayer'
            assert rankings[0]['profit_loss'] == 5000.0  # 15000 - 10000
            
            assert rankings[1]['username'] == 'WinStreak'
            assert rankings[1]['profit_loss'] == 2000.0  # 12000 - 10000
            
            assert rankings[2]['username'] == 'NewPlayer'
            assert rankings[2]['profit_loss'] == 0.0  # 10000 - 10000
            
            assert rankings[3]['username'] == 'Unlucky'
            assert rankings[3]['profit_loss'] == -2000.0  # 8000 - 10000
    
    def test_win_rate_ranking(self, app, leaderboard_test_users):
        """Test ranking by win percentage"""
        with app.app_context():
            rankings = get_leaderboard_rankings('win_rate', limit=10)
            
            # Should only include users with bets and order by win rate
            assert len(rankings) == 3  # NewPlayer excluded (no bets)
            
            # WinStreak should be first (90% win rate)
            assert rankings[0]['username'] == 'WinStreak'
            assert rankings[0]['win_percentage'] == 90.0
            
            # TopPlayer second (75% win rate)
            assert rankings[1]['username'] == 'TopPlayer'
            assert rankings[1]['win_percentage'] == 75.0
            
            # Unlucky last (20% win rate)
            assert rankings[2]['username'] == 'Unlucky'
            assert rankings[2]['win_percentage'] == 20.0
    
    def test_total_winnings_ranking(self, app, leaderboard_test_users):
        """Test ranking by total winnings"""
        with app.app_context():
            rankings = get_leaderboard_rankings('winnings', limit=10)
            
            # Should be ordered by total winnings descending
            assert rankings[0]['username'] == 'TopPlayer'
            assert rankings[0]['total_winnings'] == 8000.0
            
            assert rankings[1]['username'] == 'WinStreak'
            assert rankings[1]['total_winnings'] == 3000.0
            
            assert rankings[2]['username'] == 'Unlucky'
            assert rankings[2]['total_winnings'] == 1500.0
    
    def test_ranking_limit(self, app, leaderboard_test_users):
        """Test that ranking limit is respected"""
        with app.app_context():
            rankings = get_leaderboard_rankings('balance', limit=2)
            
            assert len(rankings) == 2
            assert rankings[0]['username'] == 'TopPlayer'
            assert rankings[1]['username'] == 'WinStreak'
    
    def test_ranking_includes_required_fields(self, app, leaderboard_test_users):
        """Test that ranking includes all required fields"""
        with app.app_context():
            rankings = get_leaderboard_rankings('balance', limit=1)
            
            ranking = rankings[0]
            required_fields = [
                'rank', 'username', 'discord_id', 'balance', 
                'total_bets', 'winning_bets', 'win_percentage',
                'total_winnings', 'profit_loss'
            ]
            
            for field in required_fields:
                assert field in ranking


class TestLeaderboardRoutes:
    """Test leaderboard web routes"""
    
    def test_leaderboard_route_accessible(self, app, leaderboard_test_users):
        """Test that leaderboard route is accessible"""
        with app.test_client() as client:
            response = client.get('/stats/leaderboard')
            assert response.status_code == 200
    
    def test_leaderboard_sorts_by_balance_default(self, app, leaderboard_test_users):
        """Test that leaderboard defaults to balance sorting"""
        with app.test_client() as client:
            response = client.get('/stats/leaderboard')
            
            # Check that response contains users in balance order
            data = response.get_data(as_text=True)
            assert 'TopPlayer' in data
            # TopPlayer should appear before WinStreak
            top_pos = data.find('TopPlayer')
            win_pos = data.find('WinStreak')
            assert top_pos < win_pos
    
    def test_leaderboard_sort_parameter(self, app, leaderboard_test_users):
        """Test leaderboard sorting with different parameters"""
        with app.test_client() as client:
            # Test win rate sorting
            response = client.get('/stats/leaderboard?sort=win_rate')
            assert response.status_code == 200
            
            # Test profit sorting
            response = client.get('/stats/leaderboard?sort=profit')
            assert response.status_code == 200
            
            # Test winnings sorting
            response = client.get('/stats/leaderboard?sort=winnings')
            assert response.status_code == 200
    
    def test_leaderboard_with_no_users(self, app):
        """Test leaderboard with no users in database"""
        with app.test_client() as client:
            response = client.get('/stats/leaderboard')
            assert response.status_code == 200
            # Should not crash with empty user list


class TestLeaderboardCalculations:
    """Test leaderboard calculation functions"""
    
    def test_win_percentage_calculation_with_bets(self, app):
        """Test win percentage calculation for users with bets"""
        with app.app_context():
            user = User(
                discord_id='calc_test_1',
                username='TestCalc',
                balance=10000.0,
                starting_balance=10000.0,
                total_bets=10,
                winning_bets=7,
                losing_bets=3
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.win_percentage == 70.0
    
    def test_win_percentage_calculation_no_bets(self, app):
        """Test win percentage calculation for users with no bets"""
        with app.app_context():
            user = User(
                discord_id='calc_test_2',
                username='TestNoBets',
                balance=10000.0,
                starting_balance=10000.0,
                total_bets=0,
                winning_bets=0,
                losing_bets=0
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.win_percentage == 0.0
    
    def test_profit_loss_calculation(self, app):
        """Test profit/loss calculation"""
        with app.app_context():
            # Profit scenario
            user1 = User(
                discord_id='profit_test_1',
                username='Profitable',
                balance=12000.0,
                starting_balance=10000.0
            )
            db.session.add(user1)
            
            # Loss scenario  
            user2 = User(
                discord_id='profit_test_2',
                username='Losing',
                balance=8000.0,
                starting_balance=10000.0
            )
            db.session.add(user2)
            db.session.commit()
            
            assert user1.profit_loss == 2000.0
            assert user2.profit_loss == -2000.0


class TestLeaderboardUI:
    """Test leaderboard UI components"""
    
    def test_leaderboard_displays_user_stats(self, app, leaderboard_test_users):
        """Test that leaderboard displays user statistics"""
        with app.test_client() as client:
            response = client.get('/stats/leaderboard')
            data = response.get_data(as_text=True)
            
            # Check that key user information is displayed
            assert 'TopPlayer' in data
            assert '15,000' in data or '$15,000' in data  # Balance formatting
            assert '75' in data  # Win percentage
    
    def test_leaderboard_sorting_buttons(self, app, leaderboard_test_users):
        """Test that leaderboard has sorting options"""
        with app.test_client() as client:
            response = client.get('/stats/leaderboard')
            data = response.get_data(as_text=True)
            
            # Check for sorting links/buttons
            assert 'sort=balance' in data or 'Balance' in data
            assert 'sort=win_rate' in data or 'Win Rate' in data
            assert 'sort=profit' in data or 'Profit' in data