import pytest
from unittest.mock import patch, MagicMock
from flask import url_for
from app import create_app, db
from app.models import User


class TestFlaskDiscordAuth:
    """Test Discord OAuth authentication functionality"""
    
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
    
    def test_app_factory_creates_app(self, app):
        """Test that application factory creates Flask app"""
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_discord_oauth_configured(self, app):
        """Test that Flask-Discord is properly configured"""
        # Check that Discord OAuth extension is registered
        assert hasattr(app, 'discord')
        
        # Check required configuration is present
        assert 'DISCORD_CLIENT_ID' in app.config
        assert 'DISCORD_CLIENT_SECRET' in app.config
        assert 'DISCORD_REDIRECT_URI' in app.config
    
    def test_login_route_exists(self, client):
        """Test that login route is accessible"""
        response = client.get('/login')
        assert response.status_code in [200, 302]  # 302 for redirect to Discord
    
    def test_logout_route_exists(self, client):
        """Test that logout route is accessible"""  
        response = client.get('/logout')
        assert response.status_code == 302  # Should redirect after logout
    
    def test_callback_route_exists(self, client):
        """Test that OAuth callback route exists"""
        response = client.get('/callback')
        # Should return error without proper OAuth params, but route should exist
        assert response.status_code in [400, 401, 302]
    
    @patch('flask_discord.DiscordOAuth2Session.fetch_user')
    def test_oauth_callback_creates_user(self, mock_fetch_user, client, app):
        """Test that OAuth callback creates user in database"""
        # Mock Discord user data
        mock_user_data = MagicMock()
        mock_user_data.id = '123456789'
        mock_user_data.username = 'testuser'
        mock_user_data.discriminator = '1234'
        mock_user_data.display_name = 'Test User'
        mock_user_data.avatar_url = 'https://cdn.discordapp.com/avatars/123/avatar.png'
        
        mock_fetch_user.return_value = mock_user_data
        
        with app.app_context():
            # Simulate OAuth callback
            with patch('flask_discord.DiscordOAuth2Session.callback') as mock_callback:
                mock_callback.return_value = True
                
                # Should create user in database
                user_count_before = User.query.count()
                
                # Trigger callback (this would normally be called by Discord)
                # For now, just test the user creation logic directly
                user = User.create_from_discord(mock_user_data)
                db.session.add(user)
                db.session.commit()
                
                user_count_after = User.query.count()
                assert user_count_after == user_count_before + 1
                
                # Verify user data
                created_user = User.query.filter_by(discord_id='123456789').first()
                assert created_user is not None
                assert created_user.username == 'testuser'
                assert created_user.discriminator == '1234'
    
    def test_session_management(self, app):
        """Test that session management is properly configured"""
        assert 'SESSION_TYPE' in app.config
        assert app.config.get('SESSION_PERMANENT') is False
        assert 'SECRET_KEY' in app.config
    
    def test_unauthorized_user_redirected_to_login(self, client):
        """Test that unauthorized users are redirected to login"""
        # Try to access protected route (dashboard)
        response = client.get('/dashboard')
        assert response.status_code == 302
        
        # Check that redirect goes to login
        assert '/login' in response.location or 'discord' in response.location.lower()


class TestDiscordOAuthFlow:
    """Test the complete Discord OAuth flow"""
    
    @pytest.fixture  
    def app(self):
        """Create test Flask application"""
        app = create_app('testing')
        app.config['TESTING'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @patch('flask_discord.DiscordOAuth2Session.create_session')
    def test_login_redirects_to_discord(self, mock_create_session, app):
        """Test that login initiates Discord OAuth"""
        mock_create_session.return_value = 'https://discord.com/oauth2/authorize?...'
        
        with app.test_client() as client:
            response = client.get('/login')
            
            # Should redirect to Discord OAuth
            assert response.status_code == 302
            mock_create_session.assert_called_once()
    
    def test_protected_routes_require_authentication(self, app):
        """Test that protected routes require authentication"""
        with app.test_client() as client:
            protected_routes = ['/dashboard', '/betting/games', '/stats/profile']
            
            for route in protected_routes:
                response = client.get(route, follow_redirects=False)
                # Should redirect to login or return 401
                assert response.status_code in [302, 401]


# Test configuration requirements
def test_required_discord_config():
    """Test that required Discord configuration is validated"""
    # This will fail until we add the Discord config validation
    with pytest.raises(ValueError):
        app = create_app('testing')
        app.config.pop('DISCORD_CLIENT_ID', None)
        app.config.pop('DISCORD_CLIENT_SECRET', None)
        # Should raise error about missing Discord configuration
        app.discord  # Access discord extension to trigger validation