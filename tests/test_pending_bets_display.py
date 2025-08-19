"""
Tests for pending bets display on user dashboard

Tests the display of current unresolved bets including:
- Query for pending bets
- Bet details formatting
- Responsive design integration
- Dashboard layout enhancement
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Game, Bet


class TestPendingBetsDisplay:
    """Test suite for pending bets display feature"""
    
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
                balance=10000.00,
                starting_balance=10000.00
            )
            db.session.add(user)
            db.session.commit()
            # Refresh to ensure we have the ID
            db.session.refresh(user)
            user_id = user.id
            discord_id = user.discord_id
            # Return a dict with necessary data to avoid session issues
            return {'id': user_id, 'discord_id': discord_id}
    
    @pytest.fixture
    def test_games(self, app):
        """Create test games for betting"""
        with app.app_context():
            # Future game 1
            game1 = Game(
                espn_game_id='game1',
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow() + timedelta(days=2),
                week=1,
                season=2025,
                status='scheduled'
            )
            
            # Future game 2
            game2 = Game(
                espn_game_id='game2',
                home_team='Team C',
                away_team='Team D',
                game_time=datetime.utcnow() + timedelta(days=3),
                week=1,
                season=2025,
                status='scheduled'
            )
            
            # Past game (completed)
            game3 = Game(
                espn_game_id='game3',
                home_team='Team E',
                away_team='Team F',
                game_time=datetime.utcnow() - timedelta(days=1),
                week=1,
                season=2025,
                status='final',
                home_score=21,
                away_score=14
            )
            
            db.session.add_all([game1, game2, game3])
            db.session.commit()
            
            # Return game IDs and team names to avoid session issues
            return [
                {'id': game1.id, 'home_team': game1.home_team, 'away_team': game1.away_team},
                {'id': game2.id, 'home_team': game2.home_team, 'away_team': game2.away_team},
                {'id': game3.id, 'home_team': game3.home_team, 'away_team': game3.away_team}
            ]
    
    @pytest.fixture
    def pending_bets(self, app, test_user, test_games):
        """Create pending bets for test user"""
        with app.app_context():
            bets = []
            
            # Pending bet on game 1
            bet1 = Bet(
                user_id=test_user['id'],
                game_id=test_games[0]['id'],
                team_picked=test_games[0]['home_team'],
                wager_amount=100.00,
                potential_payout=200.00,
                status='pending'
            )
            bets.append(bet1)
            
            # Pending bet on game 2
            bet2 = Bet(
                user_id=test_user['id'],
                game_id=test_games[1]['id'],
                team_picked=test_games[1]['away_team'],
                wager_amount=250.00,
                potential_payout=500.00,
                status='pending'
            )
            bets.append(bet2)
            
            # Settled bet (should not appear in pending)
            bet3 = Bet(
                user_id=test_user['id'],
                game_id=test_games[2]['id'],
                team_picked=test_games[2]['home_team'],
                wager_amount=50.00,
                potential_payout=100.00,
                status='won'
            )
            bets.append(bet3)
            
            db.session.add_all(bets)
            db.session.commit()
            return bets
    
    def test_dashboard_shows_pending_bets_section(self, client, test_user, pending_bets):
        """Test that dashboard displays pending bets section"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Check for pending bets section
        assert b'Pending Bets' in response.data or b'Current Bets' in response.data
        
        # Check that pending bets are displayed
        assert b'Team A' in response.data  # Home team from bet1
        assert b'Team D' in response.data  # Away team from bet2
        assert b'$100.00' in response.data  # Wager from bet1
        assert b'$250.00' in response.data  # Wager from bet2
        
        # Check that settled bet is NOT displayed
        assert b'Team E' not in response.data  # Should not show completed game
    
    def test_pending_bets_show_game_details(self, client, test_user, pending_bets):
        """Test that pending bets display includes game details"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Check for game time display
        data = response.data.decode('utf-8')
        assert 'Team A vs Team B' in data or ('Team A' in data and 'Team B' in data)
        assert 'Team C vs Team D' in data or ('Team C' in data and 'Team D' in data)
    
    def test_pending_bets_show_potential_payout(self, client, test_user, pending_bets):
        """Test that pending bets display potential payout"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Check for potential payout display
        assert b'$200.00' in response.data  # Potential payout from bet1
        assert b'$500.00' in response.data  # Potential payout from bet2
    
    def test_no_pending_bets_message(self, client, test_user):
        """Test message when user has no pending bets"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        # Check for no pending bets message
        data = response.data.decode('utf-8')
        assert 'No pending bets' in data or 'no active bets' in data.lower()
    
    def test_pending_bets_responsive_design(self, client, test_user, pending_bets):
        """Test that pending bets section uses responsive design classes"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        
        # Check for responsive grid classes
        assert 'grid' in data
        assert any(cls in data for cls in ['md:grid-cols', 'lg:grid-cols', 'sm:grid-cols'])
    
    def test_pending_bets_count_display(self, client, test_user, pending_bets):
        """Test that the count of pending bets is displayed"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        # Should show 2 pending bets
        assert '2' in data and ('pending' in data.lower() or 'active' in data.lower())
    
    def test_pending_bets_ordered_by_game_time(self, client, test_user, pending_bets):
        """Test that pending bets are ordered by game time"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        
        # Team A game should appear before Team C game (sooner game time)
        team_a_pos = data.find('Team A')
        team_c_pos = data.find('Team C')
        
        if team_a_pos != -1 and team_c_pos != -1:
            assert team_a_pos < team_c_pos  # Team A should appear first