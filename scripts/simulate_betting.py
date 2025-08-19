#!/usr/bin/env python3
"""
Betting and Settlement Simulation Script

This script allows you to simulate the full betting lifecycle:
1. Place bets on upcoming games
2. Complete games with simulated results
3. Settle bets automatically
4. View updated leaderboard with real settlement data
"""

import random
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Game, Bet, Transaction
from app.services.settlement_service import SettlementService

def get_users_with_bets():
    """Get users who have at least one bet to simulate with"""
    return User.query.filter(User.total_bets > 0).all()

def get_scheduled_games():
    """Get games that are scheduled and can accept bets"""
    return Game.query.filter_by(status='scheduled').all()

def place_random_bets(users, games, num_bets=10):
    """Place random bets for simulation"""
    print(f"\n=== Placing {num_bets} Random Bets ===")
    
    bets_placed = []
    
    for i in range(num_bets):
        user = random.choice(users)
        game = random.choice(games)
        
        # Check if user already has a bet on this game
        existing_bet = Bet.query.filter_by(user_id=user.id, game_id=game.id).first()
        if existing_bet:
            continue
            
        # Random bet details
        team_picked = random.choice([game.home_team, game.away_team])
        wager_amount = random.randint(50, 500)
        potential_payout = wager_amount * 2.0  # 2:1 odds
        
        # Check if user has enough balance
        if user.balance < wager_amount:
            print(f"  Skipping bet - {user.username} has insufficient balance (${user.balance:.2f} < ${wager_amount})")
            continue
            
        # Create the bet
        bet = Bet(
            user_id=user.id,
            game_id=game.id,
            team_picked=team_picked,
            wager_amount=wager_amount,
            potential_payout=potential_payout,
            status='pending',
            placed_at=datetime.utcnow() - timedelta(minutes=random.randint(10, 1440))  # Bet placed 10min to 24hrs ago
        )
        
        # Deduct wager from user balance
        user.balance -= wager_amount
        
        # Create transaction record for bet placement
        transaction = Transaction(
            user_id=user.id,
            type='bet_placed',
            amount=-wager_amount,
            balance_before=user.balance + wager_amount,
            balance_after=user.balance,
            bet_id=None,  # Will be set after bet is created
            description=f"Bet placed: {team_picked} vs {game.home_team if team_picked == game.away_team else game.away_team}"
        )
        
        db.session.add(bet)
        db.session.add(transaction)
        db.session.flush()  # Get the bet ID
        
        transaction.bet_id = bet.id
        bets_placed.append(bet)
        
        print(f"  PLACED: {user.username} bet ${wager_amount} on {team_picked} vs {game.home_team if team_picked == game.away_team else game.away_team}")
    
    db.session.commit()
    print(f"\nSUCCESS: Placed {len(bets_placed)} bets successfully!")
    return bets_placed

def complete_games_with_results(games_to_complete=3):
    """Complete scheduled games with random results"""
    print(f"\n=== Completing {games_to_complete} Games ===")
    
    scheduled_games = get_scheduled_games()
    if len(scheduled_games) < games_to_complete:
        games_to_complete = len(scheduled_games)
        print(f"  Only {games_to_complete} scheduled games available")
    
    completed_games = []
    
    for i in range(games_to_complete):
        game = scheduled_games[i]
        
        # Generate random scores
        home_score = random.randint(14, 35)
        away_score = random.randint(14, 35)
        
        # Avoid ties for simplicity (make one team win by at least 1)
        if home_score == away_score:
            if random.random() > 0.5:
                home_score += random.randint(1, 7)
            else:
                away_score += random.randint(1, 7)
        
        # Update game status
        game.status = 'final'
        game.home_score = home_score
        game.away_score = away_score
        game.winner = game.home_team if home_score > away_score else game.away_team
        game.is_tie = False
        
        completed_games.append(game)
        
        print(f"  RESULT: {game.away_team} {away_score} - {home_score} {game.home_team} (Winner: {game.winner})")
    
    db.session.commit()
    print(f"\nSUCCESS: Completed {len(completed_games)} games!")
    return completed_games

def settle_completed_games():
    """Use the settlement service to settle all bets for completed games"""
    print(f"\n=== Settling Bets ===")
    
    settlement_service = SettlementService()
    result = settlement_service.settle_completed_games()
    
    if result['success']:
        print(f"  SUCCESS: Settlement completed successfully!")
        print(f"  STATS: Games processed: {result['games_processed']}")
        print(f"  STATS: Bets settled: {result['bets_settled']}")
        
        if result['errors']:
            print(f"  WARNING: Errors encountered: {len(result['errors'])}")
            for error in result['errors']:
                print(f"    - Bet {error['bet_id']}: {error['error']}")
    else:
        print(f"  ERROR: Settlement failed: {result.get('error', 'Unknown error')}")
    
    return result

def show_leaderboard_summary():
    """Show a summary of the current leaderboard"""
    print(f"\n=== Updated Leaderboard Summary ===")
    
    users = User.query.order_by(User.balance.desc()).limit(10).all()
    
    print(f"{'Rank':<4} {'Username':<15} {'Balance':<12} {'P&L':<10} {'Total Winnings':<15} {'Win Rate':<8}")
    print("-" * 80)
    
    for rank, user in enumerate(users, 1):
        profit_loss = user.profit_loss
        win_rate = user.win_percentage if user.total_bets > 0 else 0
        
        profit_loss_str = f"+${profit_loss:.2f}" if profit_loss >= 0 else f"-${abs(profit_loss):.2f}"
        
        print(f"{rank:<4} {user.username:<15} ${user.balance:<11.2f} {profit_loss_str:<10} ${user.total_winnings:<14.2f} {win_rate:.1f}%")

def show_recent_settlements():
    """Show recent settled bets"""
    print(f"\n=== Recent Settlements ===")
    
    recent_bets = Bet.query.filter(
        Bet.status.in_(['won', 'lost', 'push'])
    ).order_by(Bet.settled_at.desc()).limit(10).all()
    
    if not recent_bets:
        print("  No settled bets found.")
        return
    
    print(f"{'User':<15} {'Team Picked':<20} {'Result':<6} {'Wager':<8} {'Payout':<8}")
    print("-" * 65)
    
    for bet in recent_bets:
        payout_str = f"${bet.actual_payout:.2f}" if bet.actual_payout > 0 else "$0.00"
        print(f"{bet.user.username:<15} {bet.team_picked:<20} {bet.status:<6} ${bet.wager_amount:<7.2f} {payout_str}")

def main():
    """Main simulation function"""
    app = create_app('development')
    
    with app.app_context():
        print("NFL Betting Simulation Starting...")
        print("=" * 50)
        
        # Get available data
        users = get_users_with_bets()
        games = get_scheduled_games()
        
        print(f"Found {len(users)} users with betting history")
        print(f"Found {len(games)} scheduled games")
        
        if len(users) == 0:
            print("ERROR: No users with betting history found. Run seed_test_data.py first.")
            return
            
        if len(games) == 0:
            print("ERROR: No scheduled games found. All games may already be completed.")
            return
        
        # Step 1: Place some random bets
        new_bets = place_random_bets(users, games, num_bets=8)
        
        # Step 2: Complete some games
        completed_games = complete_games_with_results(games_to_complete=3)
        
        # Step 3: Settle the bets
        settlement_result = settle_completed_games()
        
        # Step 4: Show results
        show_recent_settlements()
        show_leaderboard_summary()
        
        print(f"\nSimulation Complete!")
        print("You can now view the updated leaderboard in the web app to see:")
        print("   - Real settlement data (Total Winnings will no longer be $0)")
        print("   - Updated balances from actual wins/losses")
        print("   - Accurate win rate calculations")
        print("\nVisit http://127.0.0.1:5000/stats/leaderboard to see the results!")

if __name__ == '__main__':
    main()