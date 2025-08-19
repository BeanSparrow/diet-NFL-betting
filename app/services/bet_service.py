"""
Bet validation service for form validation and business logic

Provides validation for betting forms including:
- Amount validation
- Balance validation  
- Game timing validation
- Duplicate bet validation
"""

from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta, timezone
from flask import flash

from app.models import User, Game, Bet
from app import db


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class BetValidator:
    """Validator for betting operations and form validation"""
    
    def __init__(self):
        self.errors = []
    
    def validate_bet_amount(self, user: User, amount: Union[str, float]) -> bool:
        """Validate bet amount against user balance and minimum requirements"""
        try:
            # Convert to float if string
            if isinstance(amount, str):
                amount = float(amount)
            
            # Check if amount is positive
            if amount <= 0:
                self.errors.append("Bet amount must be greater than zero")
                return False
            
            # Check minimum bet amount (from config)
            from flask import current_app
            min_bet = current_app.config.get('MIN_BET_AMOUNT', 1)
            if amount < min_bet:
                self.errors.append(f"Minimum bet amount is ${min_bet}")
                return False
            
            # Check user balance
            if amount > user.balance:
                self.errors.append(f"Insufficient balance. You have ${user.balance:.2f}")
                return False
            
            return True
            
        except (ValueError, TypeError):
            self.errors.append("Invalid bet amount")
            return False
    
    def validate_game_timing(self, game: Game) -> bool:
        """Validate that game is still available for betting (5-minute cutoff before start)"""
        if not game:
            self.errors.append("Game not found")
            return False
        
        # Handle both naive and aware datetimes
        if game.game_time.tzinfo is None:
            # If game_time is naive, assume it's UTC
            game_time_utc = game.game_time.replace(tzinfo=timezone.utc)
        else:
            game_time_utc = game.game_time
            
        cutoff_time = game_time_utc - timedelta(minutes=5)
        now = datetime.now(timezone.utc)
        
        # Check if game has already started
        if game_time_utc <= now:
            self.errors.append("Cannot bet on games that have already started")
            return False
        
        # Check if within 5-minute cutoff window
        if now >= cutoff_time:
            self.errors.append("Cannot place bets within 5 minutes before game start")
            return False
        
        # Check game status
        if game.status not in ['scheduled', 'pre']:
            self.errors.append("Game is no longer available for betting")
            return False
        
        return True
    
    def validate_team_selection(self, game: Game, team_picked: str) -> bool:
        """Validate that selected team is valid for the game"""
        if not team_picked:
            self.errors.append("Please select a team")
            return False
        
        if team_picked not in [game.home_team, game.away_team]:
            self.errors.append("Invalid team selection")
            return False
        
        return True
    
    def validate_duplicate_bet(self, user: User, game: Game) -> bool:
        """Check if user already has a bet on this game"""
        existing_bet = Bet.query.filter_by(
            user_id=user.id,
            game_id=game.id,
            status='pending'
        ).first()
        
        if existing_bet:
            self.errors.append("You already have a pending bet on this game")
            return False
        
        return True
    
    def validate_bet_comprehensive(self, user: User, game_id: int, 
                                  team_picked: str, wager_amount: Union[str, float]) -> bool:
        """Perform comprehensive bet validation"""
        self.errors = []  # Reset errors
        
        # Get game
        game = Game.query.get(game_id)
        if not game:
            self.errors.append("Game not found")
            return False
        
        # Run all validations
        validations = [
            self.validate_bet_amount(user, wager_amount),
            self.validate_game_timing(game),
            self.validate_team_selection(game, team_picked),
            self.validate_duplicate_bet(user, game)
        ]
        
        return all(validations)
    
    def get_errors(self) -> List[str]:
        """Get list of validation errors"""
        return self.errors
    
    def flash_errors(self):
        """Flash validation errors to user"""
        for error in self.errors:
            flash(error, 'error')
    
    def create_bet(self, user: User, game_id: int, team_picked: str, 
                   wager_amount: float) -> Optional[Bet]:
        """Create a new bet after validation"""
        try:
            # Validate first
            if not self.validate_bet_comprehensive(user, game_id, team_picked, wager_amount):
                return None
            
            # Convert amount to float if needed
            if isinstance(wager_amount, str):
                wager_amount = float(wager_amount)
            
            # Get game
            game = Game.query.get(game_id)
            
            # Calculate potential payout
            from flask import current_app
            multiplier = current_app.config.get('PAYOUT_MULTIPLIER', 2.0)
            potential_payout = wager_amount * multiplier
            
            # Create bet
            bet = Bet(
                user_id=user.id,
                game_id=game_id,
                team_picked=team_picked,
                wager_amount=wager_amount,
                potential_payout=potential_payout,
                status='pending'
            )
            
            # Update user balance
            user.balance -= wager_amount
            
            # Save to database
            db.session.add(bet)
            db.session.commit()
            
            return bet
            
        except Exception as e:
            db.session.rollback()
            self.errors.append("Failed to place bet. Please try again.")
            return None
    
    def cancel_bet(self, user: User, bet_id: int) -> bool:
        """Cancel a pending bet and refund the wager amount"""
        self.errors = []  # Reset errors
        
        try:
            # Get the bet
            bet = Bet.query.filter_by(
                id=bet_id,
                user_id=user.id
            ).first()
            
            if not bet:
                self.errors.append("Bet not found or not owned by user")
                return False
            
            # Check if bet is still cancellable
            if bet.status != 'pending':
                self.errors.append("Only pending bets can be cancelled")
                return False
            
            # Check if within 5-minute cutoff window
            cutoff_time = bet.game.game_time - timedelta(minutes=5)
            now = datetime.now(timezone.utc)
            
            if now >= cutoff_time:
                self.errors.append("Cannot cancel bets within 5 minutes before game start")
                return False
            
            # Update bet status
            bet.status = 'cancelled'
            bet.settled_at = datetime.now(timezone.utc)
            
            # Refund the wager amount
            user.balance += bet.wager_amount
            
            # Commit the transaction atomically
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            self.errors.append("Failed to cancel bet. Please try again.")
            return False


class FormValidator:
    """General form validation helper"""
    
    @staticmethod
    def validate_required_fields(form_data: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
        """Validate that all required fields are present"""
        errors = []
        
        for field in required_fields:
            if field not in form_data or not form_data[field]:
                errors.append(f"{field.replace('_', ' ').title()} is required")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_numeric_field(value: Union[str, int, float], field_name: str) -> Tuple[bool, Optional[str]]:
        """Validate that a field is numeric"""
        try:
            float(value)
            return True, None
        except (ValueError, TypeError):
            return False, f"{field_name} must be a valid number"
    
    @staticmethod
    def validate_positive_number(value: Union[str, int, float], field_name: str) -> Tuple[bool, Optional[str]]:
        """Validate that a field is a positive number"""
        try:
            num_value = float(value)
            if num_value <= 0:
                return False, f"{field_name} must be greater than zero"
            return True, None
        except (ValueError, TypeError):
            return False, f"{field_name} must be a valid positive number"


def validate_bet_form(form_data: Dict, user: User) -> Tuple[bool, List[str]]:
    """
    Validate betting form data
    
    Args:
        form_data: Form data dictionary
        user: Current user
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = BetValidator()
    form_validator = FormValidator()
    
    # Check required fields
    required_fields = ['game_id', 'team_picked', 'wager_amount']
    fields_valid, field_errors = form_validator.validate_required_fields(form_data, required_fields)
    
    if not fields_valid:
        return False, field_errors
    
    # Validate game_id is numeric
    game_id_valid, game_id_error = form_validator.validate_numeric_field(
        form_data['game_id'], 'Game ID'
    )
    if not game_id_valid:
        return False, [game_id_error]
    
    # Validate wager_amount is positive number
    amount_valid, amount_error = form_validator.validate_positive_number(
        form_data['wager_amount'], 'Wager amount'
    )
    if not amount_valid:
        return False, [amount_error]
    
    # Comprehensive bet validation
    is_valid = validator.validate_bet_comprehensive(
        user,
        int(form_data['game_id']),
        form_data['team_picked'],
        form_data['wager_amount']
    )
    
    return is_valid, validator.get_errors()