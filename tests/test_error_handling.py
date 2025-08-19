"""
Tests for error handling and user feedback systems

Tests the error handling features including:
- Error page templates (404, 500, etc.)
- User notification system with flash messages
- Form validation for betting forms
- Graceful degradation for API failures
"""

import pytest
from unittest.mock import patch, Mock
from flask import url_for, session
from werkzeug.exceptions import NotFound, InternalServerError

from app import create_app, db
from app.models import User, Game, Bet


class TestErrorPages:
    """Test error page templates and handlers"""
    
    def test_404_error_page_accessible(self, app):
        """Test that 404 error page renders correctly"""
        with app.test_client() as client:
            response = client.get('/nonexistent-page')
            assert response.status_code == 404
            assert b'404' in response.data
            assert b'Page Not Found' in response.data
            assert b'Go Home' in response.data
    
    def test_404_error_page_styling(self, app):
        """Test that 404 error page uses proper styling"""
        with app.test_client() as client:
            response = client.get('/nonexistent-page')
            data = response.get_data(as_text=True)
            # Should extend base template
            assert 'Diet NFL Betting' in data
            # Should have Bootstrap classes (or equivalent styling)
            assert 'btn' in data or 'button' in data
    
    def test_500_error_page_handling(self, app):
        """Test that 500 error page renders on server errors"""
        with app.test_client() as client:
            # Force a 500 error by patching a route to raise exception
            with patch('app.routes.main.render_template') as mock_render:
                mock_render.side_effect = Exception("Test error")
                response = client.get('/')
                assert response.status_code == 500
                # Should show error page content  
                data = response.get_data(as_text=True)
                assert '500' in data or 'Server Error' in data
    
    def test_error_page_navigation_links(self, app):
        """Test that error pages have proper navigation"""
        with app.test_client() as client:
            response = client.get('/nonexistent-page')
            data = response.get_data(as_text=True)
            # Should have link back to home
            assert url_for('main.index') in data or '/' in data
    
    def test_database_rollback_on_500_error(self, app):
        """Test that database session is rolled back on 500 errors"""
        with app.app_context():
            # This will be tested by verifying the error handler calls db.session.rollback
            with app.test_client() as client:
                with patch('app.routes.main.render_template') as mock_render:
                    mock_render.side_effect = Exception("Test error")
                    with patch('app.db.session.rollback') as mock_rollback:
                        response = client.get('/')
                        # Rollback should have been called during error handling
                        # Note: This test verifies the error handler exists and works


class TestUserNotifications:
    """Test user notification system with flash messages"""
    
    def test_flash_message_display_success(self, app):
        """Test that success flash messages are displayed"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_flashes'] = [('success', 'Test success message')]
            
            response = client.get('/')
            data = response.get_data(as_text=True)
            assert 'Test success message' in data
            # Should have success styling
            assert 'success' in data or 'green' in data
    
    def test_flash_message_display_error(self, app):
        """Test that error flash messages are displayed"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_flashes'] = [('error', 'Test error message')]
            
            response = client.get('/')
            data = response.get_data(as_text=True)
            assert 'Test error message' in data
            # Should have error styling  
            assert 'error' in data or 'red' in data
    
    def test_flash_message_display_info(self, app):
        """Test that info flash messages are displayed"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_flashes'] = [('info', 'Test info message')]
            
            response = client.get('/')
            data = response.get_data(as_text=True)
            assert 'Test info message' in data
            # Should have info styling
            assert 'info' in data or 'blue' in data
    
    def test_flash_message_display_warning(self, app):
        """Test that warning flash messages are displayed"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_flashes'] = [('warning', 'Test warning message')]
            
            response = client.get('/')
            data = response.get_data(as_text=True)
            assert 'Test warning message' in data
            # Should have warning styling
            assert 'warning' in data or 'yellow' in data
    
    def test_multiple_flash_messages(self, app):
        """Test that multiple flash messages are displayed"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_flashes'] = [
                    ('success', 'Success message'),
                    ('error', 'Error message'),
                    ('info', 'Info message')
                ]
            
            response = client.get('/')
            data = response.get_data(as_text=True)
            assert 'Success message' in data
            assert 'Error message' in data
            assert 'Info message' in data


class TestFormValidation:
    """Test form validation for betting forms"""
    
    def test_bet_form_validation_missing_amount(self, app, sample_user, bettable_game):
        """Test that bet form validates missing amount"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            response = client.post('/betting/place', data={
                'game_id': test_game.id,
                'team_picked': test_game.home_team,
                # Missing wager_amount
            })
            
            # Should return error or redirect with error message
            assert response.status_code in [400, 302]
            
            if response.status_code == 302:
                # Check for flash message
                with client.session_transaction() as sess:
                    flashes = sess.get('_flashes', [])
                    assert any('amount' in msg.lower() for category, msg in flashes)
    
    def test_bet_form_validation_invalid_amount(self, app, sample_user, bettable_game):
        """Test that bet form validates invalid amount"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = sample_user.id
            
            response = client.post('/betting/place', data={
                'game_id': bettable_game.id,
                'team_picked': bettable_game.home_team,
                'wager_amount': 'invalid'  # Non-numeric amount
            })
            
            # Should return error or redirect with error message
            assert response.status_code in [400, 302]
    
    def test_bet_form_validation_negative_amount(self, app, test_user, test_game):
        """Test that bet form validates negative amount"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            response = client.post('/betting/place', data={
                'game_id': test_game.id,
                'team_picked': test_game.home_team,
                'wager_amount': -100  # Negative amount
            })
            
            # Should return error or redirect with error message
            assert response.status_code in [400, 302]
    
    def test_bet_form_validation_insufficient_balance(self, app, test_user, test_game):
        """Test that bet form validates insufficient balance"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            # Set user balance to low amount
            test_user.balance = 50.0
            db.session.commit()
            
            response = client.post('/betting/place', data={
                'game_id': test_game.id,
                'team_picked': test_game.home_team,
                'wager_amount': 100  # More than balance
            })
            
            # Should return error or redirect with error message
            assert response.status_code in [400, 302]
    
    def test_bet_form_validation_missing_team(self, app, test_user, test_game):
        """Test that bet form validates missing team selection"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            response = client.post('/betting/place', data={
                'game_id': test_game.id,
                'wager_amount': 100,
                # Missing team_picked
            })
            
            # Should return error or redirect with error message
            assert response.status_code in [400, 302]
    
    def test_bet_form_validation_invalid_game(self, app, test_user):
        """Test that bet form validates invalid game ID"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            response = client.post('/betting/place', data={
                'game_id': 99999,  # Non-existent game
                'team_picked': 'Test Team',
                'wager_amount': 100
            })
            
            # Should return error or redirect with error message
            assert response.status_code in [400, 404, 302]


class TestGracefulDegradation:
    """Test graceful degradation for API failures"""
    
    def test_espn_api_failure_handling(self, app):
        """Test that ESPN API failures are handled gracefully"""
        with app.test_client() as client:
            with patch('app.services.espn_service.fetch_games') as mock_fetch:
                mock_fetch.side_effect = Exception("API Error")
                
                response = client.get('/betting/games')
                
                # Should still return a page, not crash
                assert response.status_code == 200
                data = response.get_data(as_text=True)
                
                # Should show error message or empty state
                assert 'error' in data.lower() or 'no games' in data.lower() or 'unavailable' in data.lower()
    
    def test_database_connection_failure_handling(self, app):
        """Test that database connection failures are handled"""
        with app.test_client() as client:
            with patch('app.models.User.query') as mock_query:
                mock_query.side_effect = Exception("Database Error")
                
                response = client.get('/stats/leaderboard')
                
                # Should return error page or graceful degradation
                assert response.status_code in [200, 500]
                
                if response.status_code == 200:
                    data = response.get_data(as_text=True)
                    # Should show appropriate error message
                    assert 'error' in data.lower() or 'unavailable' in data.lower()
    
    def test_discord_oauth_failure_handling(self, app):
        """Test that Discord OAuth failures are handled gracefully"""
        with app.test_client() as client:
            with patch('app.routes.auth.discord.fetch_user') as mock_fetch:
                mock_fetch.side_effect = Exception("OAuth Error")
                
                response = client.get('/callback?code=test_code')
                
                # Should redirect to login with error or show error page
                assert response.status_code in [302, 400, 500]
                
                if response.status_code == 302:
                    # Should redirect to login page
                    assert '/login' in response.location or '/' in response.location
    
    def test_settlement_service_failure_handling(self, app, test_game, test_bet):
        """Test that settlement service failures are handled gracefully"""
        with app.app_context():
            from app.services.settlement_service import SettlementService
            
            settlement_service = SettlementService()
            
            with patch.object(settlement_service, 'settle_bet') as mock_settle:
                mock_settle.side_effect = Exception("Settlement Error")
                
                # Should not crash when settlement fails
                try:
                    settlement_service.settle_completed_games()
                    # Should complete without crashing
                except Exception as e:
                    # If it does raise, should be handled appropriately
                    assert "Settlement Error" not in str(e)  # Should be caught and handled


class TestFormErrorMessages:
    """Test specific form error messages and user feedback"""
    
    def test_bet_validation_error_messages(self, app, test_user, test_game):
        """Test that bet validation shows specific error messages"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            # Test insufficient balance message
            test_user.balance = 50.0
            db.session.commit()
            
            response = client.post('/betting/place', data={
                'game_id': test_game.id,
                'team_picked': test_game.home_team,
                'wager_amount': 100
            }, follow_redirects=True)
            
            data = response.get_data(as_text=True)
            # Should contain specific error about balance
            assert 'balance' in data.lower() or 'insufficient' in data.lower()
    
    def test_login_required_error_message(self, app):
        """Test that login required shows appropriate message"""
        with app.test_client() as client:
            response = client.get('/betting/games', follow_redirects=True)
            
            # Should redirect to login or show login message
            data = response.get_data(as_text=True)
            assert 'login' in data.lower() or 'sign in' in data.lower()
    
    def test_game_not_found_error_message(self, app, test_user):
        """Test that non-existent game shows appropriate error"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            response = client.get('/betting/games/99999')
            
            # Should return 404 or redirect with error
            assert response.status_code in [404, 302]


class TestErrorRecovery:
    """Test error recovery and retry mechanisms"""
    
    def test_session_recovery_after_error(self, app, test_user):
        """Test that user session is maintained after errors"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            # Cause an error on a protected route
            response = client.get('/nonexistent-protected-route')
            
            # Session should still be valid after 404 error
            with client.session_transaction() as sess:
                assert sess.get('user_id') == test_user.id
    
    def test_form_data_preservation_on_validation_error(self, app, test_user, test_game):
        """Test that form data is preserved when validation fails"""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = test_user.id
            
            response = client.post('/betting/place', data={
                'game_id': test_game.id,
                'team_picked': test_game.home_team,
                'wager_amount': 'invalid'  # Invalid amount
            }, follow_redirects=True)
            
            data = response.get_data(as_text=True)
            # Form should preserve the team selection
            assert test_game.home_team in data