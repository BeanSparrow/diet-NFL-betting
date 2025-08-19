"""
Tests for betting history page functionality

Tests the betting history display including:
- History page accessibility
- Filtering by bet status
- Pagination controls
- Query optimization
- Responsive design
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Game, Bet


class TestBettingHistory:
    """Test suite for betting history feature"""
    
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
            # Return a dict with necessary data to avoid session issues
            return {'id': user_id, 'discord_id': discord_id}
    
    @pytest.fixture
    def test_games(self, app):
        """Create test games for betting"""
        with app.app_context():
            games = []
            
            # Past game (final)
            game1 = Game(
                espn_game_id='final_game',
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow() - timedelta(days=2),
                week=1,
                season=2025,
                status='final',
                home_score=21,
                away_score=14,
                winner='Team A'
            )
            games.append(game1)
            
            # Another past game (final)
            game2 = Game(
                espn_game_id='final_game_2',
                home_team='Team C',
                away_team='Team D',
                game_time=datetime.utcnow() - timedelta(days=1),
                week=1,
                season=2025,
                status='final',
                home_score=17,
                away_score=20,
                winner='Team D'
            )
            games.append(game2)
            
            # Future game (scheduled)
            game3 = Game(
                espn_game_id='scheduled_game',
                home_team='Team E',
                away_team='Team F',
                game_time=datetime.utcnow() + timedelta(days=1),
                week=2,
                season=2025,
                status='scheduled'
            )
            games.append(game3)
            
            db.session.add_all(games)
            db.session.commit()
            
            # Return game IDs to avoid session issues
            return [{'id': game.id, 'home_team': game.home_team, 'away_team': game.away_team, 'winner': getattr(game, 'winner', None)} for game in games]
    
    @pytest.fixture
    def test_bets(self, app, test_user, test_games):
        """Create test bets with different statuses"""
        with app.app_context():
            bets = []
            
            # Won bet
            bet1 = Bet(
                user_id=test_user['id'],
                game_id=test_games[0]['id'],
                team_picked=test_games[0]['winner'],  # Pick winner
                wager_amount=100.00,
                potential_payout=200.00,
                actual_payout=200.00,
                status='won',
                placed_at=datetime.utcnow() - timedelta(days=3),
                settled_at=datetime.utcnow() - timedelta(days=2)
            )
            bets.append(bet1)
            
            # Lost bet
            bet2 = Bet(
                user_id=test_user['id'],
                game_id=test_games[1]['id'],
                team_picked=test_games[1]['home_team'],  # Pick loser
                wager_amount=50.00,
                potential_payout=100.00,
                actual_payout=0.00,
                status='lost',
                placed_at=datetime.utcnow() - timedelta(days=2),
                settled_at=datetime.utcnow() - timedelta(days=1)
            )
            bets.append(bet2)
            
            # Pending bet
            bet3 = Bet(
                user_id=test_user['id'],
                game_id=test_games[2]['id'],
                team_picked=test_games[2]['home_team'],
                wager_amount=75.00,
                potential_payout=150.00,
                status='pending',
                placed_at=datetime.utcnow() - timedelta(hours=1)
            )
            bets.append(bet3)
            
            db.session.add_all(bets)
            db.session.commit()
            
            return [{'id': bet.id, 'status': bet.status, 'wager_amount': bet.wager_amount} for bet in bets]
    
    def test_betting_history_page_accessible(self, client, test_user):
        """Test that betting history page is accessible to logged-in users"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        assert b'Betting History' in response.data
    
    def test_betting_history_requires_login(self, client):
        """Test that betting history redirects unauthorized users"""
        response = client.get('/betting/history')
        assert response.status_code == 302  # Redirect to login
    
    def test_betting_history_displays_all_bets(self, client, test_user, test_bets):
        """Test that all user bets are displayed in history"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        # Check that all three bets are displayed
        data = response.data.decode('utf-8')
        assert 'Team A' in data  # Won bet
        assert 'Team C' in data  # Lost bet  
        assert 'Team E' in data  # Pending bet
    
    def test_betting_history_filter_by_status_won(self, client, test_user, test_bets):
        """Test filtering betting history by won status"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history?status=won')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        assert 'Team A' in data  # Won bet should be shown
        assert 'Team C' not in data  # Lost bet should not be shown
        assert 'Team E' not in data  # Pending bet should not be shown
    
    def test_betting_history_filter_by_status_lost(self, client, test_user, test_bets):
        """Test filtering betting history by lost status"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history?status=lost')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        assert 'Team A' not in data  # Won bet should not be shown
        assert 'Team C' in data  # Lost bet should be shown
        assert 'Team E' not in data  # Pending bet should not be shown
    
    def test_betting_history_filter_by_status_pending(self, client, test_user, test_bets):
        """Test filtering betting history by pending status"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history?status=pending')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        assert 'Team A' not in data  # Won bet should not be shown
        assert 'Team C' not in data  # Lost bet should not be shown
        assert 'Team E' in data  # Pending bet should be shown
    
    def test_betting_history_filter_controls_display(self, client, test_user, test_bets):
        """Test that filter controls are displayed correctly"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        assert 'All Bets' in data
        assert 'Pending' in data
        assert 'Won' in data
        assert 'Lost' in data
        assert 'Push' in data
    
    def test_betting_history_active_filter_highlight(self, client, test_user, test_bets):
        """Test that active filter is highlighted"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        # Test won filter active
        response = client.get('/betting/history?status=won')
        assert response.status_code == 200
        data = response.data.decode('utf-8')
        
        # Check that won filter has active styling
        assert 'bg-blue-600 text-white' in data
    
    def test_betting_history_no_bets_message(self, client, test_user):
        """Test message displayed when user has no bets"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        assert 'No Betting History' in data
        assert 'Place Your First Bet' in data
    
    def test_betting_history_pagination_single_page(self, client, test_user, test_bets):
        """Test that pagination is not shown for single page results"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        # With only 3 bets and per_page=20, pagination should not appear
        assert 'fas fa-chevron-left' not in data
        assert 'fas fa-chevron-right' not in data
    
    def test_betting_history_displays_bet_amounts(self, client, test_user, test_bets):
        """Test that bet amounts are correctly displayed"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        assert '$100.00' in data  # Won bet wager
        assert '$50.00' in data   # Lost bet wager
        assert '$75.00' in data   # Pending bet wager
    
    def test_betting_history_displays_game_details(self, client, test_user, test_bets):
        """Test that game details are displayed in history"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        # Check for game matchup format
        assert 'Team B @ Team A' in data
        assert 'Team D @ Team C' in data
        assert 'Team F @ Team E' in data
    
    def test_betting_history_shows_bet_status_icons(self, client, test_user, test_bets):
        """Test that bet status icons are displayed"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        assert 'fa-check' in data  # Won bet icon
        assert 'fa-times' in data  # Lost bet icon
        assert 'fa-clock' in data  # Pending bet icon
    
    def test_betting_history_ordered_by_date(self, client, test_user, test_bets):
        """Test that betting history is ordered by placement date (newest first)"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        
        # Pending bet (most recent) should appear first
        pending_pos = data.find('Team E')
        lost_pos = data.find('Team C')  
        won_pos = data.find('Team A')
        
        # Verify order: Pending (newest) -> Lost -> Won (oldest)
        assert pending_pos < lost_pos < won_pos
    
    def test_betting_history_view_details_links(self, client, test_user, test_bets):
        """Test that view details links are present"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        # Should have "View Details" links for each bet
        assert data.count('View Details') == 3
    
    def test_betting_history_shows_correct_payout_text(self, client, test_user, test_bets):
        """Test that correct payout text is shown for different bet statuses"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        assert 'Potential payout' in data  # For pending bets
        assert 'Won' in data              # For won bets
        assert 'Lost' in data             # For lost bets
    
    def test_betting_history_responsive_design_classes(self, client, test_user, test_bets):
        """Test that responsive design classes are present"""
        with client.session_transaction() as sess:
            sess['discord_user_id'] = test_user['discord_id']
        
        response = client.get('/betting/history')
        assert response.status_code == 200
        
        data = response.data.decode('utf-8')
        # Check for responsive grid classes
        assert 'md:col-span-2' in data
        assert 'grid-cols-1 md:grid-cols-3' in data
        # Check for responsive flex classes
        assert 'flex-wrap' in data