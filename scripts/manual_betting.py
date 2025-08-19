#!/usr/bin/env python3
"""
Manual Betting Control Script

This script provides individual functions for:
- Placing specific bets
- Completing specific games  
- Running settlement manually
- Viewing current status
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Game, Bet
from app.services.settlement_service import SettlementService

def list_users():
    """Show all users and their current status"""
    print("\n=== Available Users ===")
    users = User.query.all()
    
    print(f"{'ID':<3} {'Username':<15} {'Balance':<12} {'Total Bets':<10} {'Win Rate':<8}")
    print("-" * 55)
    
    for user in users:
        win_rate = user.win_percentage if user.total_bets > 0 else 0
        print(f"{user.id:<3} {user.username:<15} ${user.balance:<11.2f} {user.total_bets:<10} {win_rate:.1f}%")

def list_games(status='scheduled'):
    """Show games by status"""
    print(f"\n=== {status.title()} Games ===")
    games = Game.query.filter_by(status=status).order_by(Game.week, Game.game_time).all()
    
    print(f"{'ID':<3} {'Away Team':<20} {'Home Team':<20} {'Week':<4} {'Status':<10}")
    print("-" * 65)
    
    for game in games:
        print(f"{game.id:<3} {game.away_team:<20} {game.home_team:<20} {game.week:<4} {game.status:<10}")
    
    return games

def place_bet(user_id, game_id, team_picked, wager_amount):
    """Place a specific bet"""
    user = User.query.get(user_id)
    game = Game.query.get(game_id)
    
    if not user:
        print(f"ERROR: User {user_id} not found")
        return False
        
    if not game:
        print(f"ERROR: Game {game_id} not found")
        return False
        
    if game.status != 'scheduled':
        print(f"ERROR: Game {game_id} is not scheduled (status: {game.status})")
        return False
        
    if team_picked not in [game.home_team, game.away_team]:
        print(f"ERROR: Team '{team_picked}' is not playing in this game")
        print(f"Available teams: {game.away_team}, {game.home_team}")
        return False
        
    if user.balance < wager_amount:
        print(f"ERROR: User {user.username} has insufficient balance (${user.balance:.2f} < ${wager_amount})")
        return False
        
    # Check for existing bet
    existing_bet = Bet.query.filter_by(user_id=user_id, game_id=game_id).first()
    if existing_bet:
        print(f"ERROR: User {user.username} already has a bet on this game")
        return False
    
    # Create the bet
    bet = Bet(
        user_id=user_id,
        game_id=game_id,
        team_picked=team_picked,
        wager_amount=wager_amount,
        potential_payout=wager_amount * 2.0,  # 2:1 odds
        status='pending',
        placed_at=datetime.utcnow()
    )
    
    # Deduct wager from balance
    user.balance -= wager_amount
    
    db.session.add(bet)
    db.session.commit()
    
    print(f"SUCCESS: {user.username} bet ${wager_amount} on {team_picked}")
    print(f"Potential payout: ${bet.potential_payout}")
    print(f"New balance: ${user.balance:.2f}")
    
    return True

def complete_game(game_id, home_score, away_score):
    """Complete a game with specific scores"""
    game = Game.query.get(game_id)
    
    if not game:
        print(f"ERROR: Game {game_id} not found")
        return False
        
    if game.status != 'scheduled':
        print(f"ERROR: Game {game_id} is not scheduled (status: {game.status})")
        return False
    
    # Update game
    game.status = 'final'
    game.home_score = home_score
    game.away_score = away_score
    
    if home_score > away_score:
        game.winner = game.home_team
        game.is_tie = False
    elif away_score > home_score:
        game.winner = game.away_team  
        game.is_tie = False
    else:
        game.winner = None
        game.is_tie = True
    
    db.session.commit()
    
    print(f"SUCCESS: Game completed")
    print(f"Final Score: {game.away_team} {away_score} - {home_score} {game.home_team}")
    if game.is_tie:
        print("Result: TIE")
    else:
        print(f"Winner: {game.winner}")
    
    return True

def run_settlement():
    """Run the settlement service"""
    print("\n=== Running Settlement ===")
    settlement_service = SettlementService()
    result = settlement_service.settle_completed_games()
    
    if result['success']:
        print(f"SUCCESS: Settlement completed")
        print(f"Games processed: {result['games_processed']}")
        print(f"Bets settled: {result['bets_settled']}")
        
        if result['errors']:
            print(f"Errors: {len(result['errors'])}")
            for error in result['errors']:
                print(f"  - Bet {error['bet_id']}: {error['error']}")
    else:
        print(f"ERROR: Settlement failed - {result.get('error', 'Unknown error')}")
    
    return result

def show_pending_bets():
    """Show all pending bets"""
    print("\n=== Pending Bets ===")
    bets = Bet.query.filter_by(status='pending').join(User).join(Game).all()
    
    if not bets:
        print("No pending bets found.")
        return
    
    print(f"{'Bet ID':<6} {'User':<15} {'Team Picked':<20} {'Wager':<8} {'Game':<30}")
    print("-" * 85)
    
    for bet in bets:
        game_desc = f"{bet.game.away_team} @ {bet.game.home_team}"
        print(f"{bet.id:<6} {bet.user.username:<15} {bet.team_picked:<20} ${bet.wager_amount:<7.2f} {game_desc:<30}")

def main():
    """Interactive manual betting control"""
    app = create_app('development')
    
    with app.app_context():
        print("Manual Betting Control")
        print("=" * 50)
        
        while True:
            print("\nOptions:")
            print("1. List users")
            print("2. List scheduled games")
            print("3. List final games")
            print("4. Show pending bets")
            print("5. Place a bet")
            print("6. Complete a game")
            print("7. Run settlement")
            print("8. Exit")
            
            try:
                choice = input("\nEnter choice (1-8): ").strip()
                
                if choice == '1':
                    list_users()
                    
                elif choice == '2':
                    list_games('scheduled')
                    
                elif choice == '3':
                    list_games('final')
                    
                elif choice == '4':
                    show_pending_bets()
                    
                elif choice == '5':
                    print("\n--- Place a Bet ---")
                    try:
                        user_id = int(input("User ID: "))
                        game_id = int(input("Game ID: "))
                        team_picked = input("Team picked: ").strip()
                        wager_amount = float(input("Wager amount: $"))
                        place_bet(user_id, game_id, team_picked, wager_amount)
                    except ValueError:
                        print("ERROR: Invalid input")
                        
                elif choice == '6':
                    print("\n--- Complete a Game ---")
                    try:
                        game_id = int(input("Game ID: "))
                        away_score = int(input("Away team score: "))
                        home_score = int(input("Home team score: "))
                        complete_game(game_id, home_score, away_score)
                    except ValueError:
                        print("ERROR: Invalid input")
                        
                elif choice == '7':
                    run_settlement()
                    
                elif choice == '8':
                    print("Goodbye!")
                    break
                    
                else:
                    print("Invalid choice")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"ERROR: {e}")

if __name__ == '__main__':
    main()