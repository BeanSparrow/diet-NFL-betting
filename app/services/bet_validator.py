"""
Bet validation and storage service for Diet NFL Betting Service.

This service handles all bet validation logic including:
- Balance validation
- Game timing checks  
- Bet storage with transaction handling
- Comprehensive validation workflows

Follows scope requirements:
- Must implement: balance validation, game timing checks, bet storage, transaction handling
- Must NOT implement: bet modification, bet cancellation, advanced validation rules
"""

from datetime import datetime
from typing import Dict, Any
from sqlalchemy.exc import SQLAlchemyError
from app import db
from app.models import User, Game, Bet, Transaction


class BetValidationError(Exception):
    """Custom exception for bet validation errors"""
    pass


class BetValidator:
    """
    Service class for validating and creating bets with proper transaction handling.
    
    Implements all bet validation logic according to PRD requirements:
    - Wager amounts: Users can bet any amount > 0 up to their current balance
    - Bet validation: Prevent betting after games start
    """
    
    def validate_bet_amount(self, amount: float, user: User) -> bool:
        """
        Validate bet wager amount against user balance and business rules.
        
        Args:
            amount: Wager amount to validate
            user: User placing the bet
            
        Returns:
            True if valid
            
        Raises:
            BetValidationError: If amount is invalid
        """
        if amount is None or amount <= 0:
            raise BetValidationError("Wager amount must be greater than 0.")
        
        if amount > user.balance:
            raise BetValidationError(f"Insufficient balance. You have ${user.balance:.2f}")
        
        return True
    
    def validate_game_timing(self, game: Game) -> bool:
        """
        Validate that the game is still open for betting.
        
        Args:
            game: Game to validate timing for
            
        Returns:
            True if game is bettable
            
        Raises:
            BetValidationError: If game is no longer bettable
        """
        if not game.is_bettable:
            raise BetValidationError("This game is no longer available for betting.")
        
        return True
    
    def validate_team_selection(self, team_picked: str, game: Game) -> bool:
        """
        Validate that the selected team is valid for this game.
        
        Args:
            team_picked: Name of team user picked
            game: Game being bet on
            
        Returns:
            True if team selection is valid
            
        Raises:
            BetValidationError: If team selection is invalid
        """
        if not team_picked or team_picked not in [game.home_team, game.away_team]:
            raise BetValidationError("Invalid team selection.")
        
        return True
    
    def validate_duplicate_bet(self, user: User, game: Game) -> bool:
        """
        Validate that user doesn't already have a bet on this game.
        
        Args:
            user: User placing the bet
            game: Game being bet on
            
        Returns:
            True if no duplicate bet exists
            
        Raises:
            BetValidationError: If user already has a bet on this game
        """
        existing_bet = Bet.query.filter_by(
            user_id=user.id,
            game_id=game.id
        ).first()
        
        if existing_bet:
            raise BetValidationError("You already have a bet on this game.")
        
        return True
    
    def validate_bet(self, bet_data: Dict[str, Any], user: User, game: Game) -> bool:
        """
        Perform comprehensive bet validation.
        
        Args:
            bet_data: Dictionary containing bet information
            user: User placing the bet
            game: Game being bet on
            
        Returns:
            True if all validations pass
            
        Raises:
            BetValidationError: If any validation fails
        """
        # Extract bet data
        team_picked = bet_data.get('team_picked')
        wager_amount = bet_data.get('wager_amount')
        
        # Run all validations
        self.validate_bet_amount(wager_amount, user)
        self.validate_game_timing(game)
        self.validate_team_selection(team_picked, game)
        self.validate_duplicate_bet(user, game)
        
        return True
    
    def create_bet(self, bet_data: Dict[str, Any], user: User, game: Game) -> Bet:
        """
        Create a new bet with proper transaction handling.
        
        Args:
            bet_data: Dictionary containing bet information
            user: User placing the bet
            game: Game being bet on
            
        Returns:
            Created Bet object
            
        Raises:
            BetValidationError: If bet creation fails
            SQLAlchemyError: If database transaction fails
        """
        team_picked = bet_data['team_picked']
        wager_amount = bet_data['wager_amount']
        
        try:
            # Create bet object
            bet = Bet(
                user_id=user.id,
                game_id=game.id,
                team_picked=team_picked,
                wager_amount=wager_amount,
                potential_payout=wager_amount * 2,  # Double or nothing
                status='pending'
            )
            
            # Update user balance and statistics
            user.balance -= wager_amount
            user.total_bets += 1
            
            # Update game statistics
            game.total_bets += 1
            game.total_wagered += wager_amount
            if team_picked == game.home_team:
                game.home_bets += 1
            else:
                game.away_bets += 1
            
            # Create transaction record for audit trail
            transaction = Transaction(
                user_id=user.id,
                type='bet_placed',
                amount=-wager_amount,
                balance_before=user.balance + wager_amount,
                balance_after=user.balance,
                bet_id=None,  # Will be set after bet.id is available
                description=f'Bet placed on {team_picked} vs {game.home_team if team_picked == game.away_team else game.away_team}'
            )
            
            # Add all objects to session
            db.session.add(bet)
            db.session.add(transaction)
            
            # Commit transaction
            db.session.commit()
            
            # Update transaction with bet ID after commit
            transaction.bet_id = bet.id
            db.session.commit()
            
            return bet
            
        except SQLAlchemyError as e:
            # Rollback on any database error
            db.session.rollback()
            raise BetValidationError(f"Failed to create bet: {str(e)}")
    
    def validate_and_create_bet(self, bet_data: Dict[str, Any], user: User, game: Game) -> Bet:
        """
        Complete workflow: validate bet and create if valid.
        
        Args:
            bet_data: Dictionary containing bet information
            user: User placing the bet
            game: Game being bet on
            
        Returns:
            Created Bet object
            
        Raises:
            BetValidationError: If validation fails or bet creation fails
        """
        # First validate the bet
        self.validate_bet(bet_data, user, game)
        
        # If validation passes, create the bet
        return self.create_bet(bet_data, user, game)