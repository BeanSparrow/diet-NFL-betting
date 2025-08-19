import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from app import db
from app.models import User, Game, Bet, get_current_user
from flask import session


class TestUserModel:
    """Test User model with Discord integration and SQLAlchemy 2.0 features"""
    
    def test_user_model_creation(self, app):
        """Test User model can be created with required fields"""
        with app.app_context():
            user = User(
                discord_id='123456789',
                username='testuser',
                discriminator='1234',
                display_name='Test User',
                avatar_url='https://cdn.discordapp.com/avatars/123/avatar.png'
            )
            db.session.add(user)
            db.session.commit()
            
            # Verify user was created
            saved_user = User.query.filter_by(discord_id='123456789').first()
            assert saved_user is not None
            assert saved_user.username == 'testuser'
            assert saved_user.discriminator == '1234'
            assert saved_user.balance == 10000.0  # Default starting balance
            assert saved_user.starting_balance == 10000.0
    
    def test_user_discord_id_unique_constraint(self, app):
        """Test that discord_id must be unique"""
        with app.app_context():
            user1 = User(discord_id='123456789', username='user1')
            user2 = User(discord_id='123456789', username='user2')
            
            db.session.add(user1)
            db.session.commit()
            
            db.session.add(user2)
            with pytest.raises(Exception):  # Should raise integrity error
                db.session.commit()
    
    def test_create_from_discord_method(self, app):
        """Test User.create_from_discord class method"""
        with app.app_context():
            # Mock Discord user object
            mock_discord_user = MagicMock()
            mock_discord_user.id = 987654321
            mock_discord_user.username = 'discorduser'
            mock_discord_user.discriminator = '5678'
            mock_discord_user.display_name = 'Discord User'
            mock_discord_user.avatar_url = 'https://cdn.discordapp.com/avatars/987/avatar.png'
            
            user = User.create_from_discord(mock_discord_user)
            db.session.add(user)
            db.session.commit()
            
            # Verify user creation
            assert user.discord_id == '987654321'
            assert user.username == 'discorduser'
            assert user.discriminator == '5678'
            assert user.display_name == 'Discord User'
            assert user.balance == 10000.0
            assert user.starting_balance == 10000.0
    
    def test_update_from_discord_method(self, app):
        """Test User.update_from_discord method"""
        with app.app_context():
            user = User(
                discord_id='123456789',
                username='oldname',
                discriminator='0000'
            )
            db.session.add(user)
            db.session.commit()
            
            # Mock updated Discord user
            mock_discord_user = MagicMock()
            mock_discord_user.username = 'newname'
            mock_discord_user.discriminator = '1111'
            mock_discord_user.display_name = 'New Display'
            mock_discord_user.avatar_url = 'https://new-avatar.png'
            
            user.update_from_discord(mock_discord_user)
            db.session.commit()
            
            # Verify update
            assert user.username == 'newname'
            assert user.discriminator == '1111'
            assert user.display_name == 'New Display'
            assert user.avatar_url == 'https://new-avatar.png'
    
    def test_user_win_percentage_property(self, app):
        """Test win percentage calculation"""
        with app.app_context():
            user = User(discord_id='123', username='test')
            user.total_bets = 10
            user.winning_bets = 7
            
            assert user.win_percentage == 70.0
            
            # Test zero bets
            user.total_bets = 0
            assert user.win_percentage == 0.0
    
    def test_user_profit_loss_property(self, app):
        """Test profit/loss calculation"""
        with app.app_context():
            user = User(discord_id='123', username='test')
            user.balance = 12000.0
            user.starting_balance = 10000.0
            
            assert user.profit_loss == 2000.0
            
            # Test loss
            user.balance = 8000.0
            assert user.profit_loss == -2000.0


class TestGameModel:
    """Test Game model with ESPN data integration"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask application"""
        app = create_app('testing')
        app.config['TESTING'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_game_model_creation(self, app):
        """Test Game model can be created with ESPN data"""
        with app.app_context():
            game_time = datetime.utcnow() + timedelta(days=1)
            game = Game(
                espn_game_id='401547439',
                week=1,
                season=2024,
                home_team='Kansas City Chiefs',
                home_team_abbr='KC',
                away_team='Detroit Lions',
                away_team_abbr='DET',
                game_time=game_time,
                status='scheduled'
            )
            db.session.add(game)
            db.session.commit()
            
            # Verify game creation
            saved_game = Game.query.filter_by(espn_game_id='401547439').first()
            assert saved_game is not None
            assert saved_game.home_team == 'Kansas City Chiefs'
            assert saved_game.away_team == 'Detroit Lions'
            assert saved_game.week == 1
            assert saved_game.season == 2024
            assert saved_game.status == 'scheduled'
    
    def test_game_espn_id_unique_constraint(self, app):
        """Test that espn_game_id must be unique"""
        with app.app_context():
            game1 = Game(
                espn_game_id='401547439',
                week=1,
                season=2024,
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow()
            )
            game2 = Game(
                espn_game_id='401547439',  # Same ESPN ID
                week=2,
                season=2024,
                home_team='Team C',
                away_team='Team D',
                game_time=datetime.utcnow()
            )
            
            db.session.add(game1)
            db.session.commit()
            
            db.session.add(game2)
            with pytest.raises(Exception):  # Should raise integrity error
                db.session.commit()
    
    def test_game_is_bettable_property(self, app):
        """Test is_bettable property logic"""
        with app.app_context():
            # Future game - should be bettable
            future_game = Game(
                espn_game_id='401547440',
                week=1,
                season=2024,
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow() + timedelta(hours=2),
                status='scheduled'
            )
            assert future_game.is_bettable is True
            
            # Past game - should not be bettable
            past_game = Game(
                espn_game_id='401547441',
                week=1,
                season=2024,
                home_team='Team C',
                away_team='Team D',
                game_time=datetime.utcnow() - timedelta(hours=2),
                status='scheduled'
            )
            assert past_game.is_bettable is False
            
            # In progress game - should not be bettable
            active_game = Game(
                espn_game_id='401547442',
                week=1,
                season=2024,
                home_team='Team E',
                away_team='Team F',
                game_time=datetime.utcnow() + timedelta(hours=2),
                status='in_progress'
            )
            assert active_game.is_bettable is False
    
    def test_game_bet_percentage_properties(self, app):
        """Test home/away bet percentage calculations"""
        with app.app_context():
            game = Game(
                espn_game_id='401547443',
                week=1,
                season=2024,
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow(),
                total_bets=10,
                home_bets=7,
                away_bets=3
            )
            
            assert game.home_bet_percentage == 70.0
            assert game.away_bet_percentage == 30.0
            
            # Test zero bets
            game.total_bets = 0
            assert game.home_bet_percentage == 0.0
            assert game.away_bet_percentage == 0.0


class TestBetModel:
    """Test Bet model with relationships and constraints"""
    
    def test_bet_model_creation(self, app):
        """Test Bet model creation with relationships"""
        with app.app_context():
            # Create user and game directly in the test context
            user = User(
                discord_id='123456789',
                username='testuser',
                balance=5000.0
            )
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            game = Game(
                espn_game_id='test_game_123',
                week=1,
                season=2024,
                home_team='Kansas City Chiefs',
                away_team='Detroit Lions',
                game_time=datetime.utcnow() + timedelta(days=1),
                status='scheduled'
            )
            db.session.add(game)
            db.session.flush()  # Get game ID
            
            bet = Bet(
                user_id=user.id,
                game_id=game.id,
                team_picked='Kansas City Chiefs',
                wager_amount=100.0,
                potential_payout=200.0
            )
            db.session.add(bet)
            db.session.commit()
            
            # Verify bet creation
            saved_bet = Bet.query.filter_by(user_id=user.id).first()
            assert saved_bet is not None
            assert saved_bet.team_picked == 'Kansas City Chiefs'
            assert saved_bet.wager_amount == 100.0
            assert saved_bet.potential_payout == 200.0
            assert saved_bet.status == 'pending'
    
    def test_bet_calculate_payout_method(self, app):
        """Test calculate_payout method"""
        with app.app_context():
            bet = Bet(
                user_id=1,
                game_id=1,
                team_picked='Team A',
                wager_amount=100.0
            )
            
            bet.calculate_payout(2.0)
            assert bet.potential_payout == 200.0
            
            bet.calculate_payout(1.5)
            assert bet.potential_payout == 150.0
    
    def test_bet_settle_method_win(self, app):
        """Test bet settlement for winning bet"""
        with app.app_context():
            bet = Bet(
                user_id=1,
                game_id=1,
                team_picked='Team A',
                wager_amount=100.0,
                potential_payout=200.0
            )
            
            bet.settle('Team A')  # User picked winning team
            
            assert bet.status == 'won'
            assert bet.actual_payout == 200.0
            assert bet.settled_at is not None
    
    def test_bet_settle_method_loss(self, app):
        """Test bet settlement for losing bet"""
        with app.app_context():
            bet = Bet(
                user_id=1,
                game_id=1,
                team_picked='Team A',
                wager_amount=100.0,
                potential_payout=200.0
            )
            
            bet.settle('Team B')  # User picked losing team
            
            assert bet.status == 'lost'
            assert bet.actual_payout == 0.0
            assert bet.settled_at is not None
    
    def test_bet_settle_method_tie(self, app):
        """Test bet settlement for tied game"""
        with app.app_context():
            bet = Bet(
                user_id=1,
                game_id=1,
                team_picked='Team A',
                wager_amount=100.0,
                potential_payout=200.0
            )
            
            bet.settle(None)  # Tie game
            
            assert bet.status == 'push'
            assert bet.actual_payout == 100.0  # Return original wager
            assert bet.settled_at is not None
    
    def test_bet_unique_constraint(self, app):
        """Test unique constraint on user_id + game_id"""
        with app.app_context():
            # Create user and game for testing
            user = User(discord_id='test_unique', username='testuser')
            game = Game(
                espn_game_id='unique_test_game',
                week=1,
                season=2024,
                home_team='Team A',
                away_team='Team B',
                game_time=datetime.utcnow() + timedelta(days=1)
            )
            db.session.add_all([user, game])
            db.session.flush()
            
            bet1 = Bet(
                user_id=user.id,
                game_id=game.id,
                team_picked='Team A',
                wager_amount=100.0,
                potential_payout=200.0
            )
            bet2 = Bet(
                user_id=user.id,
                game_id=game.id,  # Same user, same game
                team_picked='Team B',
                wager_amount=50.0,
                potential_payout=100.0
            )
            
            db.session.add(bet1)
            db.session.commit()
            
            db.session.add(bet2)
            with pytest.raises(Exception):  # Should raise integrity error
                db.session.commit()


class TestAuthHelpers:
    """Test authentication helper functions"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask application"""
        app = create_app('testing')
        app.config['TESTING'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_get_current_user_with_session(self, app):
        """Test get_current_user with valid session"""
        with app.app_context():
            # Create user
            user = User(discord_id='123456789', username='testuser')
            db.session.add(user)
            db.session.commit()
            
            with app.test_request_context():
                # Set session
                session['discord_user_id'] = '123456789'
                
                current_user = get_current_user()
                assert current_user is not None
                assert current_user.discord_id == '123456789'
                assert current_user.username == 'testuser'
    
    def test_get_current_user_no_session(self, app):
        """Test get_current_user with no session"""
        with app.app_context():
            with app.test_request_context():
                current_user = get_current_user()
                assert current_user is None
    
    def test_get_current_user_invalid_session(self, app):
        """Test get_current_user with invalid user ID in session"""
        with app.app_context():
            with app.test_request_context():
                session['discord_user_id'] = 'nonexistent'
                
                current_user = get_current_user()
                assert current_user is None