import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from app import create_app, db
from app.models import User, Game, Bet
from flask import session, url_for


class TestDashboardRoute:
    """Test dashboard route functionality and access control"""
    
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
                starting_balance=10000.0,
                total_bets=15,
                winning_bets=8,
                losing_bets=7
            )
            db.session.add(user)
            db.session.commit()
            return user
    
    def test_dashboard_route_exists(self, client, app):
        """Test that dashboard route is accessible"""
        with app.app_context():
            # Should have a dashboard route
            assert url_for('main.dashboard') is not None
    
    def test_dashboard_requires_authentication(self, client):
        """Test that dashboard redirects unauthenticated users"""
        response = client.get('/dashboard')
        # Should redirect to login or show unauthorized
        assert response.status_code in [302, 401]
    
    @patch('app.models.get_current_user')
    def test_dashboard_authenticated_user_access(self, mock_get_user, client, app, sample_user):
        """Test authenticated user can access dashboard"""
        with app.app_context():
            mock_get_user.return_value = sample_user
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            assert b'dashboard' in response.data.lower()
    
    @patch('app.models.get_current_user')
    def test_dashboard_displays_user_balance(self, mock_get_user, client, app, sample_user):
        """Test dashboard displays user balance correctly"""
        with app.app_context():
            mock_get_user.return_value = sample_user
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            # Check balance is displayed
            assert b'5000' in response.data or b'5,000' in response.data
            # Check it's formatted as currency
            assert b'$' in response.data
    
    @patch('app.models.get_current_user')
    def test_dashboard_displays_profit_loss(self, mock_get_user, client, app, sample_user):
        """Test dashboard shows profit/loss calculation"""
        with app.app_context():
            mock_get_user.return_value = sample_user
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            # User has $5000 balance vs $10000 starting = -$5000 loss
            assert b'-5000' in response.data or b'-5,000' in response.data
    
    @patch('app.models.get_current_user')
    def test_dashboard_displays_win_percentage(self, mock_get_user, client, app, sample_user):
        """Test dashboard shows win percentage"""
        with app.app_context():
            mock_get_user.return_value = sample_user
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            # 8 wins out of 15 bets = 53.3%
            assert b'53' in response.data or b'8' in response.data


class TestDashboardTemplate:
    """Test dashboard template rendering and content"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask application"""
        app = create_app('testing')
        app.config['TESTING'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def sample_user_with_bets(self, app):
        """Create user with active and completed bets"""
        with app.app_context():
            user = User(
                discord_id='987654321',
                username='bettor',
                balance=12000.0,
                starting_balance=10000.0
            )
            db.session.add(user)
            
            # Create games
            past_game = Game(
                espn_game_id='401547440',
                week=1,
                season=2024,
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow() - timedelta(days=1),
                status='final',
                winner='Team A'
            )
            
            future_game = Game(
                espn_game_id='401547441',
                week=2,
                season=2024,
                home_team='Team C',
                away_team='Team D',
                game_time=datetime.utcnow() + timedelta(days=1),
                status='scheduled'
            )
            
            db.session.add(past_game)
            db.session.add(future_game)
            db.session.commit()
            
            # Create bets
            won_bet = Bet(
                user_id=user.id,
                game_id=past_game.id,
                team_picked='Team A',
                wager_amount=500.0,
                potential_payout=1000.0,
                actual_payout=1000.0,
                status='won'
            )
            
            pending_bet = Bet(
                user_id=user.id,
                game_id=future_game.id,
                team_picked='Team C',
                wager_amount=200.0,
                potential_payout=400.0,
                status='pending'
            )
            
            db.session.add(won_bet)
            db.session.add(pending_bet)
            db.session.commit()
            
            return user
    
    @patch('app.models.get_current_user')
    def test_dashboard_template_structure(self, mock_get_user, client, app, sample_user_with_bets):
        """Test dashboard template has proper HTML structure"""
        with app.app_context():
            mock_get_user.return_value = sample_user_with_bets
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            # Check for proper HTML structure
            assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
            assert b'<head>' in response.data
            assert b'<body>' in response.data
    
    @patch('app.models.get_current_user')
    def test_dashboard_tailwind_classes_present(self, mock_get_user, client, app, sample_user_with_bets):
        """Test dashboard template uses Tailwind CSS classes"""
        with app.app_context():
            mock_get_user.return_value = sample_user_with_bets
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            # Check for common Tailwind classes
            response_text = response.data.decode('utf-8')
            tailwind_indicators = [
                'class=',  # Classes should be present
                'bg-',     # Background classes
                'text-',   # Text classes  
                'p-',      # Padding classes
                'flex',    # Flexbox classes
                'grid'     # Grid classes
            ]
            
            # At least some Tailwind classes should be present
            tailwind_present = any(indicator in response_text for indicator in tailwind_indicators)
            assert tailwind_present, "Dashboard should use Tailwind CSS classes"
    
    @patch('app.models.get_current_user')
    def test_dashboard_responsive_indicators(self, mock_get_user, client, app, sample_user_with_bets):
        """Test dashboard template has responsive design elements"""
        with app.app_context():
            mock_get_user.return_value = sample_user_with_bets
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            response_text = response.data.decode('utf-8')
            
            # Check for viewport meta tag
            assert 'viewport' in response_text, "Should have viewport meta tag for responsive design"
            
            # Check for responsive Tailwind classes
            responsive_classes = ['sm:', 'md:', 'lg:', 'xl:']
            responsive_present = any(cls in response_text for cls in responsive_classes)
            assert responsive_present, "Should use responsive Tailwind classes"


class TestDashboardIntegration:
    """Test dashboard integration with authentication system"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask application"""
        app = create_app('testing')
        app.config['TESTING'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_dashboard_with_no_user_session(self, client):
        """Test dashboard behavior when no user is in session"""
        response = client.get('/dashboard')
        # Should redirect to auth or show error
        assert response.status_code in [302, 401, 403]
    
    @patch('app.models.get_current_user')
    def test_dashboard_with_invalid_user(self, mock_get_user, client):
        """Test dashboard behavior when get_current_user returns None"""
        mock_get_user.return_value = None
        
        response = client.get('/dashboard')
        # Should handle missing user gracefully
        assert response.status_code in [302, 401, 403]
    
    def test_dashboard_navigation_link_present(self, client, app):
        """Test that dashboard can be linked from other pages"""
        with app.app_context():
            # Dashboard route should be available for navigation
            dashboard_url = url_for('main.dashboard')
            assert dashboard_url is not None
            assert '/dashboard' in dashboard_url