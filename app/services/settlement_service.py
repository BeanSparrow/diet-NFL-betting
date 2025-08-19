"""
Automated Bet Settlement Service

Handles automated settlement of bets when games are completed:
- Payout calculation for wins, losses, and ties
- Balance updates for users
- Bet status changes
- Settlement triggers integration with scheduler

Scope Requirements:
- Must implement: payout calculation, balance updates, bet status changes, settlement triggers
- Must NOT implement: manual settlement, complex payout rules, settlement reversals
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import User, Game, Bet, Transaction

logger = logging.getLogger(__name__)


class SettlementError(Exception):
    """Custom exception for settlement errors"""
    pass


class SettlementService:
    """Service class for automated bet settlement"""
    
    def __init__(self):
        """Initialize settlement service"""
        self._transaction_types = {
            'won': 'bet_won',
            'lost': 'bet_lost',
            'push': 'bet_push'
        }
    
    def settle_bet(self, bet_id: int) -> Dict[str, Any]:
        """
        Settle a single bet based on game outcome
        
        Args:
            bet_id: ID of bet to settle
            
        Returns:
            Dict containing settlement results
        """
        try:
            # Get bet with game and user data
            bet = db.session.query(Bet).join(Game).join(User).filter(
                Bet.id == bet_id
            ).first()
            
            if not bet:
                return {
                    'success': False,
                    'error': f'Bet {bet_id} not found',
                    'bet_id': bet_id
                }
            
            # Check if bet is already settled
            if bet.status != 'pending':
                return {
                    'success': False,
                    'error': f'Bet {bet_id} is already settled with status: {bet.status}',
                    'bet_id': bet_id
                }
            
            # Check if game is final
            if bet.game.status != 'final':
                return {
                    'success': False,
                    'error': f'Game {bet.game.id} is not final (status: {bet.game.status})',
                    'bet_id': bet_id
                }
            
            # Determine bet outcome
            outcome = self._determine_bet_outcome(bet)
            
            # Calculate payout
            payout = self._calculate_payout(bet, outcome)
            
            # Start database transaction
            try:
                # Update bet status
                bet.status = outcome
                bet.actual_payout = payout
                bet.settled_at = datetime.now(timezone.utc)
                
                # Update user balance and statistics
                self._update_user_after_settlement(bet.user, bet, outcome, payout)
                
                # Create transaction record
                self._create_settlement_transaction(bet.user, bet, outcome, payout)
                
                # Commit all changes
                db.session.commit()
                
                logger.info(f"Bet {bet_id} settled: {outcome}, payout: ${payout:.2f}")
                
                return {
                    'success': True,
                    'bet_id': bet_id,
                    'status': outcome,
                    'payout': payout,
                    'settled_at': bet.settled_at.isoformat()
                }
                
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error settling bet {bet_id}: {e}")
                raise SettlementError(f"Database error: {e}")
                
        except Exception as e:
            logger.error(f"Error settling bet {bet_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'bet_id': bet_id
            }
    
    def _determine_bet_outcome(self, bet: Bet) -> str:
        """
        Determine outcome of bet based on game result
        
        Args:
            bet: Bet instance to evaluate
            
        Returns:
            Outcome string: 'won', 'lost', or 'push'
        """
        game = bet.game
        
        # Handle tie games
        if game.is_tie or game.winner is None:
            return 'push'
        
        # Check if user picked the winning team
        if bet.team_picked == game.winner:
            return 'won'
        else:
            return 'lost'
    
    def _calculate_payout(self, bet: Bet, outcome: str) -> float:
        """
        Calculate payout amount based on bet outcome
        
        Args:
            bet: Bet instance
            outcome: Bet outcome ('won', 'lost', 'push')
            
        Returns:
            Payout amount
        """
        if outcome == 'won':
            return bet.potential_payout
        elif outcome == 'push':
            # Return original wager for tie games
            return bet.wager_amount
        else:  # lost
            return 0.0
    
    def _update_user_after_settlement(self, user: User, bet: Bet, outcome: str, payout: float) -> None:
        """
        Update user balance and statistics after bet settlement
        
        Args:
            user: User instance
            bet: Bet instance
            outcome: Bet outcome
            payout: Payout amount
        """
        # Update balance
        user.balance += payout
        
        # Update statistics based on outcome
        if outcome == 'won':
            user.winning_bets += 1
            user.total_winnings += payout
            
            # Update biggest win if applicable
            if payout > user.biggest_win:
                user.biggest_win = payout
                
        elif outcome == 'lost':
            user.losing_bets += 1
            user.total_losses += bet.wager_amount
            
            # Update biggest loss if applicable
            if bet.wager_amount > user.biggest_loss:
                user.biggest_loss = bet.wager_amount
        
        # Push doesn't count as win or loss, just balance adjustment
    
    def _create_settlement_transaction(self, user: User, bet: Bet, outcome: str, payout: float) -> None:
        """
        Create transaction record for settlement
        
        Args:
            user: User instance
            bet: Bet instance
            outcome: Bet outcome
            payout: Payout amount
        """
        transaction_type = self._transaction_types[outcome]
        balance_before = user.balance - payout
        
        transaction = Transaction(
            user_id=user.id,
            type=transaction_type,
            amount=payout,
            balance_before=balance_before,
            balance_after=user.balance,
            bet_id=bet.id,
            description=f"Bet settlement: {outcome} - {bet.game.away_team} @ {bet.game.home_team}"
        )
        db.session.add(transaction)
    
    def settle_completed_games(self) -> Dict[str, Any]:
        """
        Settle all pending bets for completed games
        
        Returns:
            Dict containing settlement results
        """
        try:
            # Find all final games with pending bets
            completed_games = db.session.query(Game).filter(
                and_(
                    Game.status == 'final',
                    Game.bets.any(Bet.status == 'pending')
                )
            ).all()
            
            total_games = len(completed_games)
            total_bets_settled = 0
            settlement_errors = []
            
            logger.info(f"Found {total_games} completed games with pending bets")
            
            for game in completed_games:
                # Get all pending bets for this game
                pending_bets = Bet.query.filter_by(
                    game_id=game.id,
                    status='pending'
                ).all()
                
                logger.info(f"Settling {len(pending_bets)} pending bets for game {game.id}")
                
                for bet in pending_bets:
                    result = self.settle_bet(bet.id)
                    
                    if result['success']:
                        total_bets_settled += 1
                    else:
                        settlement_errors.append({
                            'bet_id': bet.id,
                            'error': result['error']
                        })
                        logger.error(f"Failed to settle bet {bet.id}: {result['error']}")
            
            logger.info(f"Settlement complete: {total_bets_settled} bets settled across {total_games} games")
            
            return {
                'success': True,
                'games_processed': total_games,
                'bets_settled': total_bets_settled,
                'errors': settlement_errors
            }
            
        except Exception as e:
            logger.error(f"Error in batch settlement: {e}")
            return {
                'success': False,
                'error': str(e),
                'games_processed': 0,
                'bets_settled': 0
            }
    
    def add_settlement_job(self, scheduler, job_id: str, interval_minutes: int) -> Any:
        """
        Add settlement job to scheduler
        
        Args:
            scheduler: Scheduler instance
            job_id: Unique identifier for the job
            interval_minutes: How often to run settlement (in minutes)
            
        Returns:
            Scheduled job instance
        """
        if not job_id or job_id.strip() == '':
            raise ValueError("Job ID cannot be empty")
        
        if interval_minutes <= 0:
            raise ValueError("Interval must be positive")
        
        def safe_settlement():
            """Wrapper for settlement with exception handling"""
            try:
                logger.info(f"Starting automated settlement job '{job_id}'")
                result = self.settle_completed_games()
                
                if result['success']:
                    logger.info(f"Settlement completed: {result['bets_settled']} bets settled across {result['games_processed']} games")
                else:
                    logger.warning(f"Settlement failed: {result.get('error', 'Unknown error')}")
                
                return result
                
            except Exception as e:
                logger.error(f"Exception in settlement job '{job_id}': {e}")
                return {'success': False, 'error': str(e)}
        
        # Add the job (replace if exists)
        job = scheduler.add_job(
            func=safe_settlement,
            trigger='interval',
            minutes=interval_minutes,
            id=job_id,
            name=f"Bet Settlement ({interval_minutes}min)",
            replace_existing=True
        )
        
        logger.info(f"Added settlement job '{job_id}' with {interval_minutes}-minute interval")
        return job


# Convenience function for scheduled settlement
def settle_completed_games() -> Dict[str, Any]:
    """
    Convenience function for settling completed games
    Used by scheduler and manual triggers
    """
    service = SettlementService()
    return service.settle_completed_games()