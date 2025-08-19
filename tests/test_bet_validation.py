import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models import User, Game, Bet, Transaction
from app.services.bet_validator import BetValidator, BetValidationError


class TestBetValidator:
    """Test bet validation service with TDD methodology"""
    
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
    def sample_user(self, app):
        """Create sample user for testing"""
        with app.app_context():
            user = User(
                discord_id='123456789',
                username='testuser',
                balance=5000.0,
                starting_balance=10000.0
            )
            db.session.add(user)
            db.session.commit()
            return user
    
    @pytest.fixture
    def bettable_game(self, app):
        """Create a game that can be bet on"""
        with app.app_context():
            game = Game(
                espn_game_id='401547440',
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
    def non_bettable_game(self, app):
        """Create a game that cannot be bet on (started)"""
        with app.app_context():
            game = Game(
                espn_game_id='401547441',
                week=1,
                season=2024,
                home_team='Green Bay Packers',
                home_team_abbr='GB',
                away_team='Chicago Bears',
                away_team_abbr='CHI',
                game_time=datetime.utcnow() - timedelta(hours=1),
                status='in_progress'
            )
            db.session.add(game)
            db.session.commit()
            return game

    def test_bet_validator_initialization(self, app):
        """Test BetValidator can be initialized"""
        with app.app_context():
            validator = BetValidator()
            assert validator is not None
    
    def test_validate_bet_amount_valid(self, app, sample_user):
        """Test valid bet amount passes validation"""
        with app.app_context():
            validator = BetValidator()
            
            # Valid amount within balance
            result = validator.validate_bet_amount(100.0, sample_user)
            assert result is True
            
            # Maximum amount (full balance)
            result = validator.validate_bet_amount(5000.0, sample_user)
            assert result is True
            
            # Minimum valid amount
            result = validator.validate_bet_amount(0.01, sample_user)
            assert result is True
    
    def test_validate_bet_amount_invalid(self, app, sample_user):
        """Test invalid bet amounts raise validation errors"""
        with app.app_context():
            validator = BetValidator()
            
            # Zero amount
            with pytest.raises(BetValidationError, match="must be greater than 0"):
                validator.validate_bet_amount(0.0, sample_user)
            
            # Negative amount
            with pytest.raises(BetValidationError, match="must be greater than 0"):
                validator.validate_bet_amount(-10.0, sample_user)
            
            # Amount exceeding balance
            with pytest.raises(BetValidationError, match="Insufficient balance"):
                validator.validate_bet_amount(10000.0, sample_user)
            
            # None/null amount
            with pytest.raises(BetValidationError, match="must be greater than 0"):
                validator.validate_bet_amount(None, sample_user)
    
    def test_validate_game_timing_valid(self, app, bettable_game):
        """Test game timing validation for bettable games"""
        with app.app_context():
            validator = BetValidator()
            
            result = validator.validate_game_timing(bettable_game)
            assert result is True
    
    def test_validate_game_timing_invalid(self, app, non_bettable_game):
        """Test game timing validation for non-bettable games"""
        with app.app_context():
            validator = BetValidator()
            
            with pytest.raises(BetValidationError, match="no longer available for betting"):
                validator.validate_game_timing(non_bettable_game)
    
    def test_validate_team_selection_valid(self, app, bettable_game):
        """Test valid team selection passes validation"""
        with app.app_context():
            validator = BetValidator()
            
            # Home team selection
            result = validator.validate_team_selection('Kansas City Chiefs', bettable_game)
            assert result is True
            
            # Away team selection
            result = validator.validate_team_selection('Detroit Lions', bettable_game)
            assert result is True
    
    def test_validate_team_selection_invalid(self, app, bettable_game):
        """Test invalid team selection raises validation errors"""
        with app.app_context():
            validator = BetValidator()
            
            # Invalid team name
            with pytest.raises(BetValidationError, match="Invalid team selection"):
                validator.validate_team_selection('Invalid Team', bettable_game)
            
            # Empty team name
            with pytest.raises(BetValidationError, match="Invalid team selection"):
                validator.validate_team_selection('', bettable_game)
            
            # None team name
            with pytest.raises(BetValidationError, match="Invalid team selection"):
                validator.validate_team_selection(None, bettable_game)
    
    def test_validate_duplicate_bet(self, app, sample_user, bettable_game):
        """Test duplicate bet validation"""
        with app.app_context():
            validator = BetValidator()
            
            # No existing bet - should pass
            result = validator.validate_duplicate_bet(sample_user, bettable_game)
            assert result is True
            
            # Create existing bet
            existing_bet = Bet(
                user_id=sample_user.id,
                game_id=bettable_game.id,
                team_picked='Kansas City Chiefs',
                wager_amount=100.0,
                potential_payout=200.0
            )
            db.session.add(existing_bet)
            db.session.commit()
            
            # Should now raise validation error
            with pytest.raises(BetValidationError, match="already have a bet on this game"):
                validator.validate_duplicate_bet(sample_user, bettable_game)
    
    def test_validate_bet_comprehensive(self, app, sample_user, bettable_game):
        """Test comprehensive bet validation with all checks"""
        with app.app_context():
            validator = BetValidator()
            
            bet_data = {
                'team_picked': 'Kansas City Chiefs',
                'wager_amount': 100.0
            }
            
            result = validator.validate_bet(bet_data, sample_user, bettable_game)
            assert result is True
    
    def test_validate_bet_comprehensive_failures(self, app, sample_user, non_bettable_game):
        """Test comprehensive bet validation with multiple failures"""
        with app.app_context():
            validator = BetValidator()
            
            bet_data = {
                'team_picked': 'Invalid Team',
                'wager_amount': 10000.0  # Exceeds balance
            }
            
            # Should raise validation error for multiple issues
            with pytest.raises(BetValidationError):
                validator.validate_bet(bet_data, sample_user, non_bettable_game)
    
    def test_create_bet_successful(self, app, sample_user, bettable_game):
        """Test successful bet creation with transaction handling"""
        with app.app_context():
            validator = BetValidator()
            
            bet_data = {
                'team_picked': 'Kansas City Chiefs',
                'wager_amount': 100.0
            }
            
            bet = validator.create_bet(bet_data, sample_user, bettable_game)
            
            # Verify bet was created
            assert bet.id is not None
            assert bet.user_id == sample_user.id
            assert bet.game_id == bettable_game.id
            assert bet.team_picked == 'Kansas City Chiefs'
            assert bet.wager_amount == 100.0
            assert bet.potential_payout == 200.0  # Double or nothing
            assert bet.status == 'pending'
            
            # Verify user balance was updated
            updated_user = User.query.get(sample_user.id)
            assert updated_user.balance == 4900.0  # 5000 - 100
            assert updated_user.total_bets == 1
            
            # Verify game statistics were updated
            updated_game = Game.query.get(bettable_game.id)
            assert updated_game.total_bets == 1
            assert updated_game.total_wagered == 100.0
            assert updated_game.home_bets == 1
            assert updated_game.away_bets == 0
            
            # Verify transaction was created
            transaction = Transaction.query.filter_by(user_id=sample_user.id).first()
            assert transaction is not None
            assert transaction.type == 'bet_placed'
            assert transaction.amount == -100.0
            assert transaction.bet_id == bet.id
    
    def test_create_bet_away_team(self, app, sample_user, bettable_game):
        """Test bet creation for away team updates correct statistics"""
        with app.app_context():
            validator = BetValidator()
            
            bet_data = {
                'team_picked': 'Detroit Lions',  # Away team
                'wager_amount': 100.0
            }
            
            bet = validator.create_bet(bet_data, sample_user, bettable_game)
            
            # Verify game statistics for away team
            updated_game = Game.query.get(bettable_game.id)
            assert updated_game.away_bets == 1
            assert updated_game.home_bets == 0
    
    def test_create_bet_transaction_rollback_on_failure(self, app, sample_user, bettable_game):
        """Test transaction rollback when bet creation fails"""
        with app.app_context():
            validator = BetValidator()
            
            bet_data = {
                'team_picked': 'Kansas City Chiefs',
                'wager_amount': 100.0
            }
            
            # Mock a database error during commit
            with patch.object(db.session, 'commit', side_effect=Exception("Database error")):
                with pytest.raises(Exception):
                    validator.create_bet(bet_data, sample_user, bettable_game)
                
                # Verify user balance wasn't changed due to rollback
                updated_user = User.query.get(sample_user.id)
                assert updated_user.balance == 5000.0  # Original balance
                assert updated_user.total_bets == 0
                
                # Verify no bet was created
                bet_count = Bet.query.filter_by(user_id=sample_user.id).count()
                assert bet_count == 0
    
    def test_validate_and_create_bet_end_to_end(self, app, sample_user, bettable_game):
        """Test complete end-to-end bet validation and creation process"""
        with app.app_context():
            validator = BetValidator()
            
            bet_data = {
                'team_picked': 'Kansas City Chiefs',
                'wager_amount': 100.0
            }
            
            bet = validator.validate_and_create_bet(bet_data, sample_user, bettable_game)
            
            # Verify complete process worked
            assert bet.id is not None
            assert bet.status == 'pending'
            
            # Verify all side effects
            updated_user = User.query.get(sample_user.id)
            assert updated_user.balance == 4900.0
            
            updated_game = Game.query.get(bettable_game.id)
            assert updated_game.total_bets == 1
            
            transaction = Transaction.query.filter_by(user_id=sample_user.id).first()
            assert transaction is not None
    
    def test_bet_validation_error_custom_exception(self):
        """Test BetValidationError is a proper exception"""
        error = BetValidationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestBetValidationIntegration:
    """Integration tests for bet validation with actual betting routes"""
    
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
    
    def test_bet_validator_service_exists(self, app):
        """Test that BetValidator service can be imported and used"""
        with app.app_context():
            from app.services.bet_validator import BetValidator
            validator = BetValidator()
            assert validator is not None