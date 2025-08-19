"""
Pytest configuration and shared fixtures for Diet NFL Betting Service tests.

Provides common test fixtures, mock configurations, and test utilities
for comprehensive test coverage across the application.
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from app import create_app, db
from app.models import User, Game, Bet, Transaction


@pytest.fixture(scope='session')
def app():
    """Create test application instance for session scope"""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SECRET_KEY': 'test-secret-key',
        'DISCORD_CLIENT_ID': 'test-client-id',
        'DISCORD_CLIENT_SECRET': 'test-client-secret',
        'DISCORD_REDIRECT_URI': 'http://localhost:5000/auth/discord/callback'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(autouse=True)
def clean_db(app):
    """Clean database before each test"""
    with app.app_context():
        # Clean all tables
        db.session.query(Transaction).delete()
        db.session.query(Bet).delete()
        db.session.query(Game).delete()
        db.session.query(User).delete()
        db.session.commit()
        yield
        # Clean after test as well
        db.session.rollback()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing"""
    with app.app_context():
        user = User(
            discord_id='123456789',
            username='testuser',
            discriminator='1234',
            balance=5000.0,
            starting_balance=10000.0
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def sample_users(app):
    """Create multiple sample users for testing"""
    with app.app_context():
        users = []
        for i in range(3):
            user = User(
                discord_id=f'12345678{i}',
                username=f'testuser{i}',
                discriminator=f'123{i}',
                balance=5000.0 + (i * 1000),
                starting_balance=10000.0
            )
            users.append(user)
            db.session.add(user)
        
        db.session.commit()
        return users


@pytest.fixture
def bettable_game(app):
    """Create a game that is open for betting"""
    with app.app_context():
        game = Game(
            espn_game_id='test_game_123',
            week=1,
            season=2024,
            home_team='Kansas City Chiefs',
            home_team_abbr='KC',
            away_team='Detroit Lions',
            away_team_abbr='DET',
            game_time=datetime.utcnow() + timedelta(days=1),
            status='scheduled'
        )
        db.session.add(game)
        db.session.commit()
        return game


@pytest.fixture
def completed_game(app):
    """Create a completed game with results"""
    with app.app_context():
        game = Game(
            espn_game_id='test_game_456',
            week=1,
            season=2024,
            home_team='Green Bay Packers',
            home_team_abbr='GB',
            away_team='Chicago Bears',
            away_team_abbr='CHI',
            game_time=datetime.utcnow() - timedelta(days=1),
            status='final',
            home_score=24,
            away_score=17,
            winner='Green Bay Packers'
        )
        db.session.add(game)
        db.session.commit()
        return game


@pytest.fixture
def sample_games(app):
    """Create multiple games with different statuses"""
    with app.app_context():
        games = []
        
        # Future game
        future_game = Game(
            espn_game_id='future_game',
            week=2,
            season=2024,
            home_team='Buffalo Bills',
            home_team_abbr='BUF',
            away_team='Miami Dolphins',
            away_team_abbr='MIA',
            game_time=datetime.utcnow() + timedelta(days=2),
            status='scheduled'
        )
        games.append(future_game)
        
        # In progress game
        live_game = Game(
            espn_game_id='live_game',
            week=1,
            season=2024,
            home_team='New England Patriots',
            home_team_abbr='NE',
            away_team='New York Jets',
            away_team_abbr='NYJ',
            game_time=datetime.utcnow() - timedelta(hours=1),
            status='in_progress',
            quarter='Q3',
            time_remaining='8:45',
            home_score=14,
            away_score=10
        )
        games.append(live_game)
        
        # Completed game
        final_game = Game(
            espn_game_id='final_game',
            week=1,
            season=2024,
            home_team='Dallas Cowboys',
            home_team_abbr='DAL',
            away_team='Philadelphia Eagles',
            away_team_abbr='PHI',
            game_time=datetime.utcnow() - timedelta(days=1),
            status='final',
            home_score=21,
            away_score=28,
            winner='Philadelphia Eagles'
        )
        games.append(final_game)
        
        for game in games:
            db.session.add(game)
        
        db.session.commit()
        return games


@pytest.fixture
def sample_bet(app, sample_user, bettable_game):
    """Create a sample bet"""
    with app.app_context():
        bet = Bet(
            user_id=sample_user.id,
            game_id=bettable_game.id,
            team_picked=bettable_game.home_team,
            wager_amount=100.0,
            potential_payout=200.0,
            status='pending'
        )
        db.session.add(bet)
        db.session.commit()
        return bet


@pytest.fixture
def authenticated_session(client, sample_user):
    """Create authenticated session for testing"""
    with client.session_transaction() as sess:
        sess['discord_user_id'] = sample_user.discord_id
    return client


@pytest.fixture
def mock_discord_user():
    """Mock Discord user object for OAuth testing"""
    mock_user = MagicMock()
    mock_user.id = 123456789
    mock_user.username = 'testuser'
    mock_user.discriminator = '1234'
    mock_user.display_name = 'Test User'
    mock_user.avatar_url = 'https://example.com/avatar.png'
    mock_user.email = 'test@example.com'
    return mock_user


@pytest.fixture
def mock_discord_oauth(mock_discord_user):
    """Mock Discord OAuth session"""
    with patch('app.discord') as mock_discord:
        mock_discord.fetch_user.return_value = mock_discord_user
        mock_discord.authorized = True
        yield mock_discord


@pytest.fixture
def mock_espn_api():
    """Mock ESPN API responses"""
    mock_response = {
        'events': [
            {
                'id': '401547440',
                'name': 'Kansas City Chiefs at Detroit Lions',
                'shortName': 'KC @ DET',
                'date': (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z',
                'status': {
                    'type': {'name': 'Scheduled'}
                },
                'competitions': [{
                    'competitors': [
                        {
                            'homeAway': 'home',
                            'team': {
                                'displayName': 'Detroit Lions',
                                'abbreviation': 'DET'
                            },
                            'score': 0
                        },
                        {
                            'homeAway': 'away',
                            'team': {
                                'displayName': 'Kansas City Chiefs',
                                'abbreviation': 'KC'
                            },
                            'score': 0
                        }
                    ]
                }]
            }
        ]
    }
    
    with patch('app.services.espn_service.ESPNService._make_request') as mock_request:
        mock_request.return_value = mock_response
        yield mock_request


@pytest.fixture
def mock_scheduler():
    """Mock APScheduler for testing"""
    with patch('app.services.scheduler.BackgroundScheduler') as mock_scheduler_class:
        mock_scheduler_instance = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler_instance
        
        # Configure mock behavior
        mock_scheduler_instance.running = False
        mock_scheduler_instance.get_jobs.return_value = []
        
        yield mock_scheduler_instance


# Test utility functions
def create_test_user(discord_id='999999999', username='testuser_util', balance=1000.0):
    """Utility function to create test users"""
    return User(
        discord_id=discord_id,
        username=username,
        balance=balance,
        starting_balance=balance
    )


def create_test_game(espn_id='test_util_game', status='scheduled', 
                    home_team='Test Home', away_team='Test Away'):
    """Utility function to create test games"""
    return Game(
        espn_game_id=espn_id,
        week=1,
        season=2024,
        home_team=home_team,
        away_team=away_team,
        game_time=datetime.utcnow() + timedelta(days=1) if status == 'scheduled' else datetime.utcnow() - timedelta(days=1),
        status=status
    )


def create_test_bet(user_id, game_id, team_picked, wager_amount=100.0):
    """Utility function to create test bets"""
    return Bet(
        user_id=user_id,
        game_id=game_id,
        team_picked=team_picked,
        wager_amount=wager_amount,
        potential_payout=wager_amount * 2,
        status='pending'
    )


# Pytest markers configuration
pytest_plugins = []