"""
Tests for ESPN API Service

Tests the ESPN integration service including API calls, data parsing,
and database operations.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests

from app import create_app, db
from app.models import Game
from app.services.espn_service import ESPNService, ESPNAPIError, update_nfl_games


@pytest.fixture
def app():
    """Create test app"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def espn_service():
    """Create ESPN service instance"""
    return ESPNService()


@pytest.fixture
def mock_espn_response():
    """Mock ESPN API response data"""
    return {
        "events": [
            {
                "id": "401547439",
                "name": "New England Patriots at Buffalo Bills",
                "shortName": "NE @ BUF",
                "date": "2024-12-29T18:00:00Z",
                "status": {
                    "type": {
                        "name": "Final"
                    }
                },
                "competitions": [
                    {
                        "competitors": [
                            {
                                "team": {
                                    "displayName": "New England Patriots",
                                    "abbreviation": "NE"
                                },
                                "score": "21",
                                "homeAway": "away"
                            },
                            {
                                "team": {
                                    "displayName": "Buffalo Bills",
                                    "abbreviation": "BUF"
                                },
                                "score": "35",
                                "homeAway": "home"
                            }
                        ]
                    }
                ]
            },
            {
                "id": "401547440",
                "name": "Kansas City Chiefs at Denver Broncos",
                "shortName": "KC @ DEN",
                "date": "2024-12-29T21:00:00Z",
                "status": {
                    "type": {
                        "name": "Scheduled"
                    }
                },
                "competitions": [
                    {
                        "competitors": [
                            {
                                "team": {
                                    "displayName": "Kansas City Chiefs",
                                    "abbreviation": "KC"
                                },
                                "score": "0",
                                "homeAway": "away"
                            },
                            {
                                "team": {
                                    "displayName": "Denver Broncos",
                                    "abbreviation": "DEN"
                                },
                                "score": "0",
                                "homeAway": "home"
                            }
                        ]
                    }
                ]
            }
        ]
    }


class TestESPNService:
    """Test cases for ESPN service"""
    
    def test_service_initialization(self, espn_service):
        """Test service initializes correctly"""
        assert espn_service.BASE_URL == "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
        assert espn_service._min_request_interval == 1.0
        assert espn_service._max_retries == 3
        assert 'User-Agent' in espn_service.session.headers
    
    @patch('app.services.espn_service.time.sleep')
    @patch('app.services.espn_service.time.time')
    def test_rate_limiting(self, mock_time, mock_sleep, espn_service):
        """Test rate limiting functionality"""
        # Mock time to simulate rapid requests
        mock_time.side_effect = [0, 0, 0.5, 1.5]  # Multiple time() calls
        
        espn_service._rate_limit()  # First call
        espn_service._rate_limit()  # Second call - should trigger sleep
        
        # Verify sleep was called at least once (implementation may call it multiple times)
        assert mock_sleep.call_count > 0
        # Verify sleep was called with a positive value
        assert any(call[0][0] > 0 for call in mock_sleep.call_args_list)
    
    @patch('requests.Session.get')
    def test_make_request_success(self, mock_get, espn_service, mock_espn_response):
        """Test successful API request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_espn_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = espn_service._make_request("http://test.url")
        
        assert result == mock_espn_response
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    @patch('app.services.espn_service.time.sleep')
    @patch('app.services.espn_service.time.time')
    def test_make_request_rate_limited(self, mock_time, mock_sleep, mock_get, espn_service):
        """Test handling of 429 rate limit response"""
        # Mock time to avoid rate limiting delays
        mock_time.return_value = 0
        
        # Mock rate limited response followed by success
        rate_limited_response = Mock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {'Retry-After': '10'}
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "test"}
        success_response.raise_for_status.return_value = None
        
        mock_get.side_effect = [rate_limited_response, success_response]
        
        result = espn_service._make_request("http://test.url")
        
        assert result == {"data": "test"}
        # Check that ESPN rate limit sleep was called
        assert any(call[0][0] == 10 for call in mock_sleep.call_args_list)
        assert mock_get.call_count == 2
    
    @patch('requests.Session.get')
    def test_make_request_failure(self, mock_get, espn_service):
        """Test request failure after retries"""
        mock_get.side_effect = requests.RequestException("Connection error")
        
        with pytest.raises(ESPNAPIError, match="Failed to fetch data after 3 attempts"):
            espn_service._make_request("http://test.url")
        
        assert mock_get.call_count == 3  # Should retry 3 times
    
    @patch.object(ESPNService, '_make_request')
    def test_get_current_week_games(self, mock_request, espn_service, mock_espn_response):
        """Test fetching current week games"""
        mock_request.return_value = mock_espn_response
        
        result = espn_service.get_current_week_games()
        
        assert result == mock_espn_response
        mock_request.assert_called_once_with("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
    
    @patch.object(ESPNService, '_make_request')
    def test_get_games_by_week(self, mock_request, espn_service, mock_espn_response):
        """Test fetching games by specific week"""
        mock_request.return_value = mock_espn_response
        
        result = espn_service.get_games_by_week(2024, 17)
        
        assert result == mock_espn_response
        expected_params = {
            'seasontype': 2,
            'week': 17,
            'year': 2024
        }
        mock_request.assert_called_once_with(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard", 
            expected_params
        )


class TestESPNDataParsing:
    """Test cases for ESPN data parsing"""
    
    def test_parse_game_data(self, espn_service, mock_espn_response):
        """Test parsing ESPN API response"""
        result = espn_service.parse_game_data(mock_espn_response)
        
        assert len(result) == 2
        
        # Test first game (completed)
        game1 = result[0]
        assert game1['espn_game_id'] == "401547439"
        assert game1['home_team'] == "Buffalo Bills"
        assert game1['away_team'] == "New England Patriots"
        assert game1['home_team_abbrev'] == "BUF"
        assert game1['away_team_abbrev'] == "NE"
        assert game1['home_score'] == 35
        assert game1['away_score'] == 21
        assert game1['status'] == "Final"
        assert game1['completed'] is True
        assert game1['winner'] == "Buffalo Bills"
        
        # Test second game (scheduled)
        game2 = result[1]
        assert game2['espn_game_id'] == "401547440"
        assert game2['home_team'] == "Denver Broncos"
        assert game2['away_team'] == "Kansas City Chiefs"
        assert game2['status'] == "Scheduled"
        assert game2['completed'] is False
        assert game2['winner'] is None
    
    def test_parse_single_game_missing_data(self, espn_service):
        """Test parsing game with missing competition data"""
        incomplete_event = {
            "id": "401547441",
            "name": "Test Game",
            "date": "2024-12-29T18:00:00Z",
            "status": {"type": {"name": "Scheduled"}},
            "competitions": []  # Missing competitions
        }
        
        result = espn_service._parse_single_game(incomplete_event)
        assert result is None
    
    def test_parse_single_game_invalid_competitors(self, espn_service):
        """Test parsing game with invalid number of competitors"""
        invalid_event = {
            "id": "401547441",
            "name": "Test Game",
            "date": "2024-12-29T18:00:00Z",
            "status": {"type": {"name": "Scheduled"}},
            "competitions": [{
                "competitors": [  # Only one competitor
                    {
                        "team": {"displayName": "Team A", "abbreviation": "TA"},
                        "score": "0",
                        "homeAway": "home"
                    }
                ]
            }]
        }
        
        result = espn_service._parse_single_game(invalid_event)
        assert result is None


class TestESPNDatabaseOperations:
    """Test cases for database operations"""
    
    def test_create_new_game(self, app, espn_service):
        """Test creating new game in database"""
        with app.app_context():
            game_data = {
                'espn_game_id': '401547439',
                'home_team': 'Buffalo Bills',
                'away_team': 'New England Patriots',
                'home_team_abbrev': 'BUF',
                'away_team_abbrev': 'NE',
                'home_score': 35,
                'away_score': 21,
                'game_date': datetime(2024, 12, 29, 18, 0, 0),
                'status': 'Final',
                'completed': True,
                'winner': 'Buffalo Bills'
            }
            
            espn_service._create_new_game(game_data)
            db.session.commit()
            
            # Verify game was created
            game = Game.query.filter_by(espn_game_id='401547439').first()
            assert game is not None
            assert game.home_team == 'Buffalo Bills'
            assert game.away_team == 'New England Patriots'
            assert game.home_score == 35
            assert game.away_score == 21
            assert game.status == 'final'
            assert game.winner == 'Buffalo Bills'
            assert game.week >= 1 and game.week <= 22
            assert game.season == 2024
    
    def test_update_existing_game(self, app, espn_service):
        """Test updating existing game in database"""
        with app.app_context():
            # Create initial game
            game = Game(
                espn_game_id='401547439',
                home_team='Buffalo Bills',
                away_team='New England Patriots',
                home_team_abbr='BUF',
                away_team_abbr='NE',
                home_score=0,
                away_score=0,
                game_time=datetime(2024, 12, 29, 18, 0, 0),
                status='scheduled',
                week=17,
                season=2024
            )
            db.session.add(game)
            db.session.commit()
            
            # Update game data
            game_data = {
                'home_score': 35,
                'away_score': 21,
                'status': 'Final',
                'completed': True,
                'winner': 'Buffalo Bills'
            }
            
            espn_service._update_existing_game(game, game_data)
            db.session.commit()
            
            # Verify game was updated
            updated_game = Game.query.filter_by(espn_game_id='401547439').first()
            assert updated_game.home_score == 35
            assert updated_game.away_score == 21
            assert updated_game.status == 'final'
            assert updated_game.winner == 'Buffalo Bills'
            assert updated_game.is_tie is False
    
    def test_update_games_in_database(self, app, espn_service):
        """Test updating multiple games in database"""
        with app.app_context():
            games_data = [
                {
                    'espn_game_id': '401547439',
                    'home_team': 'Buffalo Bills',
                    'away_team': 'New England Patriots',
                    'home_team_abbrev': 'BUF',
                    'away_team_abbrev': 'NE',
                    'home_score': 35,
                    'away_score': 21,
                    'game_date': datetime(2024, 12, 29, 18, 0, 0),
                    'status': 'Final',
                    'completed': True,
                    'winner': 'Buffalo Bills'
                },
                {
                    'espn_game_id': '401547440',
                    'home_team': 'Denver Broncos',
                    'away_team': 'Kansas City Chiefs',
                    'home_team_abbrev': 'DEN',
                    'away_team_abbrev': 'KC',
                    'home_score': 0,
                    'away_score': 0,
                    'game_date': datetime(2024, 12, 29, 21, 0, 0),
                    'status': 'Scheduled',
                    'completed': False,
                    'winner': None
                }
            ]
            
            result = espn_service.update_games_in_database(games_data)
            
            assert result['created'] == 2
            assert result['updated'] == 0
            
            # Verify games were created
            assert Game.query.count() == 2
            game1 = Game.query.filter_by(espn_game_id='401547439').first()
            game2 = Game.query.filter_by(espn_game_id='401547440').first()
            assert game1 is not None
            assert game2 is not None


class TestESPNIntegration:
    """Integration tests for ESPN service"""
    
    @patch.object(ESPNService, 'get_current_week_games')
    def test_fetch_and_update_current_week(self, mock_get_games, app, mock_espn_response):
        """Test full fetch and update workflow"""
        mock_get_games.return_value = mock_espn_response
        
        with app.app_context():
            espn_service = ESPNService()
            result = espn_service.fetch_and_update_current_week()
            
            assert result['success'] is True
            assert result['games_processed'] == 2
            assert result['created'] == 2
            assert result['updated'] == 0
            
            # Verify games were created in database
            assert Game.query.count() == 2
    
    @patch.object(ESPNService, 'get_current_week_games')
    def test_fetch_and_update_api_error(self, mock_get_games, app):
        """Test handling of API errors during fetch"""
        mock_get_games.side_effect = ESPNAPIError("API connection failed")
        
        with app.app_context():
            espn_service = ESPNService()
            result = espn_service.fetch_and_update_current_week()
            
            assert result['success'] is False
            assert 'API connection failed' in result['error']
            assert result['games_processed'] == 0
    
    @patch('app.services.espn_service.ESPNService.fetch_and_update_current_week')
    def test_update_nfl_games_function(self, mock_fetch, app):
        """Test convenience function for updating NFL games"""
        mock_fetch.return_value = {
            'success': True,
            'games_processed': 5,
            'created': 3,
            'updated': 2
        }
        
        with app.app_context():
            result = update_nfl_games()
            
            assert result['success'] is True
            assert result['games_processed'] == 5
            mock_fetch.assert_called_once()


class TestESPNErrorHandling:
    """Test error handling scenarios"""
    
    def test_espn_api_error_creation(self):
        """Test ESPN API error exception"""
        error = ESPNAPIError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_parse_game_data_with_exception(self, espn_service):
        """Test parsing handles malformed data gracefully"""
        malformed_data = {
            "events": [
                {"id": "test", "invalid": "structure"},
                None,  # Invalid event
                {"id": "test2"}  # Missing required fields
            ]
        }
        
        # Should not raise exception, should return empty list or partial results
        result = espn_service.parse_game_data(malformed_data)
        assert isinstance(result, list)
        # Some games may be parsed successfully, others may fail gracefully
        assert len(result) <= 3