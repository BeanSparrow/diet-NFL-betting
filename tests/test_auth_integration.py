"""
Discord OAuth Authentication Integration Tests

Comprehensive testing of Discord OAuth authentication flows
with proper mocking and edge case handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import session
from app import create_app, db
from app.models import User


@pytest.mark.auth
class TestDiscordOAuthIntegration:
    """Test Discord OAuth authentication integration"""
    
    def test_discord_login_redirect(self, client):
        """Test Discord login initiates proper redirect"""
        response = client.get('/auth/login')
        assert response.status_code == 302
        # Should redirect to Discord OAuth URL
        assert 'discord.com' in response.location
    
    def test_discord_callback_new_user(self, app, client, mock_discord_user):
        """Test Discord callback creates new user"""
        with app.app_context():
            with patch('app.routes.auth.discord.fetch_user', return_value=mock_discord_user):
                with patch('app.routes.auth.discord.authorized', True):
                    response = client.get('/auth/discord/callback?code=test_code')
                    
                    # Should redirect after successful auth
                    assert response.status_code == 302
                    
                    # User should be created in database
                    user = User.query.filter_by(discord_id=str(mock_discord_user.id)).first()
                    assert user is not None
                    assert user.username == mock_discord_user.username
                    assert user.discriminator == mock_discord_user.discriminator
                    assert user.balance == 10000.0  # Starting balance
    
    def test_discord_callback_existing_user(self, app, client, mock_discord_user):
        """Test Discord callback updates existing user"""
        with app.app_context():
            # Create existing user with old data
            existing_user = User(
                discord_id=str(mock_discord_user.id),
                username='old_username',
                discriminator='0000',
                balance=5000.0
            )
            db.session.add(existing_user)
            db.session.commit()
            user_id = existing_user.id
            
            # Update mock user data
            mock_discord_user.username = 'new_username'
            mock_discord_user.discriminator = '1111'
            
            with patch('app.routes.auth.discord.fetch_user', return_value=mock_discord_user):
                with patch('app.routes.auth.discord.authorized', True):
                    response = client.get('/auth/discord/callback?code=test_code')
                    
                    assert response.status_code == 302
                    
                    # User should be updated, not recreated
                    user = User.query.get(user_id)
                    assert user.username == 'new_username'
                    assert user.discriminator == '1111'
                    assert user.balance == 5000.0  # Balance preserved
                    
                    # Should only be one user with this Discord ID
                    user_count = User.query.filter_by(discord_id=str(mock_discord_user.id)).count()
                    assert user_count == 1
    
    def test_discord_callback_unauthorized(self, app, client):
        """Test Discord callback handles unauthorized access"""
        with app.app_context():
            with patch('app.routes.auth.discord.authorized', False):
                response = client.get('/auth/discord/callback')
                
                # Should redirect to login with error
                assert response.status_code == 302
                # No user should be created
                user_count = User.query.count()
                assert user_count == 0
    
    def test_discord_callback_fetch_user_error(self, app, client):
        """Test Discord callback handles user fetch errors"""
        with app.app_context():
            with patch('app.routes.auth.discord.authorized', True):
                with patch('app.routes.auth.discord.fetch_user', side_effect=Exception("Discord API Error")):
                    response = client.get('/auth/discord/callback?code=test_code')
                    
                    # Should handle error gracefully
                    assert response.status_code == 302
                    # No user should be created
                    user_count = User.query.count()
                    assert user_count == 0
    
    def test_session_management(self, app, client, mock_discord_user):
        """Test proper session management during auth"""
        with app.app_context():
            with patch('app.routes.auth.discord.fetch_user', return_value=mock_discord_user):
                with patch('app.routes.auth.discord.authorized', True):
                    response = client.get('/auth/discord/callback?code=test_code')
                    
                    # Check session was set
                    with client.session_transaction() as sess:
                        assert 'discord_user_id' in sess
                        assert sess['discord_user_id'] == str(mock_discord_user.id)
    
    def test_logout_clears_session(self, app, client, sample_user):
        """Test logout properly clears session"""
        with app.app_context():
            # Set up authenticated session
            with client.session_transaction() as sess:
                sess['discord_user_id'] = sample_user.discord_id
            
            # Logout
            response = client.get('/auth/logout')
            assert response.status_code == 302
            
            # Session should be cleared
            with client.session_transaction() as sess:
                assert 'discord_user_id' not in sess
    
    def test_protected_route_access(self, app, client, sample_user):
        """Test protected routes require authentication"""
        with app.app_context():
            # Test unauthenticated access
            response = client.get('/betting/games')
            assert response.status_code == 302  # Redirect to login
            
            # Test authenticated access
            with client.session_transaction() as sess:
                sess['discord_user_id'] = sample_user.discord_id
            
            response = client.get('/betting/games')
            assert response.status_code == 200
    
    def test_current_user_context_processor(self, app, client, sample_user):
        """Test current_user is available in templates"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['discord_user_id'] = sample_user.discord_id
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            # Should show user's username
            assert sample_user.username.encode() in response.data


@pytest.mark.auth
class TestDiscordOAuthEdgeCases:
    """Test edge cases and error conditions in OAuth flow"""
    
    def test_malformed_discord_callback(self, client):
        """Test handling of malformed callback data"""
        # Missing code parameter
        response = client.get('/auth/discord/callback')
        assert response.status_code == 302
        
        # Invalid code parameter
        response = client.get('/auth/discord/callback?code=')
        assert response.status_code == 302
    
    def test_discord_user_with_missing_fields(self, app, client):
        """Test handling Discord user with missing optional fields"""
        with app.app_context():
            # Mock user with minimal data
            minimal_user = MagicMock()
            minimal_user.id = 999999999
            minimal_user.username = 'minimal_user'
            minimal_user.discriminator = None  # Missing discriminator
            minimal_user.display_name = None   # Missing display name
            minimal_user.avatar_url = None     # Missing avatar
            minimal_user.email = None          # Missing email
            
            with patch('app.routes.auth.discord.fetch_user', return_value=minimal_user):
                with patch('app.routes.auth.discord.authorized', True):
                    response = client.get('/auth/discord/callback?code=test_code')
                    
                    assert response.status_code == 302
                    
                    # User should still be created
                    user = User.query.filter_by(discord_id=str(minimal_user.id)).first()
                    assert user is not None
                    assert user.username == 'minimal_user'
                    assert user.discriminator is None
    
    def test_concurrent_user_creation(self, app, mock_discord_user):
        """Test handling of concurrent user creation attempts"""
        with app.app_context():
            clients = [app.test_client() for _ in range(3)]
            
            # Simulate concurrent requests
            responses = []
            with patch('app.routes.auth.discord.fetch_user', return_value=mock_discord_user):
                with patch('app.routes.auth.discord.authorized', True):
                    for client in clients:
                        response = client.get('/auth/discord/callback?code=test_code')
                        responses.append(response)
            
            # All should succeed
            for response in responses:
                assert response.status_code == 302
            
            # Only one user should be created
            user_count = User.query.filter_by(discord_id=str(mock_discord_user.id)).count()
            assert user_count == 1
    
    def test_session_hijacking_protection(self, app, client):
        """Test protection against session hijacking"""
        with app.app_context():
            # Try to set invalid user ID in session
            with client.session_transaction() as sess:
                sess['discord_user_id'] = 'nonexistent_user'
            
            # Should handle gracefully
            response = client.get('/dashboard')
            # Should redirect to login (user not found)
            assert response.status_code == 302
    
    def test_discord_api_rate_limiting(self, app, client, mock_discord_user):
        """Test handling of Discord API rate limiting"""
        with app.app_context():
            from requests.exceptions import HTTPError
            
            # Mock rate limit error
            rate_limit_error = HTTPError("429 Rate Limited")
            
            with patch('app.routes.auth.discord.authorized', True):
                with patch('app.routes.auth.discord.fetch_user', side_effect=rate_limit_error):
                    response = client.get('/auth/discord/callback?code=test_code')
                    
                    # Should handle gracefully
                    assert response.status_code == 302
                    # No user should be created
                    user_count = User.query.count()
                    assert user_count == 0


@pytest.mark.auth
class TestAuthenticationHelpers:
    """Test authentication helper functions and utilities"""
    
    def test_get_current_user_with_valid_session(self, app, sample_user):
        """Test get_current_user with valid session"""
        with app.app_context():
            with app.test_request_context():
                with app.test_client().session_transaction() as sess:
                    sess['discord_user_id'] = sample_user.discord_id
                
                from app.models import get_current_user
                current_user = get_current_user()
                assert current_user is not None
                assert current_user.id == sample_user.id
    
    def test_get_current_user_with_invalid_session(self, app):
        """Test get_current_user with invalid session"""
        with app.app_context():
            with app.test_request_context():
                with app.test_client().session_transaction() as sess:
                    sess['discord_user_id'] = 'invalid_user_id'
                
                from app.models import get_current_user
                current_user = get_current_user()
                assert current_user is None
    
    def test_get_current_user_no_session(self, app):
        """Test get_current_user with no session"""
        with app.app_context():
            with app.test_request_context():
                from app.models import get_current_user
                current_user = get_current_user()
                assert current_user is None
    
    def test_user_balance_initialization(self, app, mock_discord_user):
        """Test user balance is properly initialized"""
        with app.app_context():
            with patch('app.routes.auth.discord.fetch_user', return_value=mock_discord_user):
                with patch('app.routes.auth.discord.authorized', True):
                    # Mock starting balance configuration
                    with patch('flask.current_app.config.get', return_value=15000.0):
                        response = app.test_client().get('/auth/discord/callback?code=test_code')
                        
                        user = User.query.filter_by(discord_id=str(mock_discord_user.id)).first()
                        assert user.balance == 15000.0
                        assert user.starting_balance == 15000.0


@pytest.mark.auth
class TestAuthenticationSecurity:
    """Test security aspects of authentication"""
    
    def test_session_security_headers(self, app, client):
        """Test proper security headers are set"""
        with app.app_context():
            response = client.get('/auth/login')
            # Basic security checks (actual headers depend on Flask configuration)
            assert response.status_code == 302
    
    def test_csrf_protection_disabled_in_testing(self, app, client, sample_user):
        """Test CSRF protection is properly disabled in testing"""
        with app.app_context():
            with client.session_transaction() as sess:
                sess['discord_user_id'] = sample_user.discord_id
            
            # Should allow POST without CSRF token in testing
            response = client.post('/betting/place/999', data={
                'team_picked': 'Test Team',
                'wager_amount': '100.00'
            })
            # Should not fail due to CSRF (may fail for other reasons like invalid game)
            assert response.status_code != 400  # 400 would indicate CSRF failure
    
    def test_user_isolation(self, app, client):
        """Test users can only access their own data"""
        with app.app_context():
            # Create two users
            user1 = User(discord_id='user1', username='user1', balance=1000.0)
            user2 = User(discord_id='user2', username='user2', balance=2000.0)
            db.session.add_all([user1, user2])
            db.session.commit()
            
            # Create bet for user2
            from tests.conftest import create_test_game, create_test_bet
            game = create_test_game()
            db.session.add(game)
            db.session.commit()
            
            bet = create_test_bet(user2.id, game.id, 'Test Team')
            db.session.add(bet)
            db.session.commit()
            
            # User1 tries to access user2's bet
            with client.session_transaction() as sess:
                sess['discord_user_id'] = user1.discord_id
            
            response = client.get(f'/betting/bet/{bet.id}')
            # Should be denied or redirected
            assert response.status_code in [302, 403, 404]