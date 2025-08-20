#!/usr/bin/env python3
"""
Fix user statistics by recalculating them from actual bet data
This script will:
1. Recalculate total_bets, winning_bets, losing_bets for all users
2. Recalculate total_winnings, total_losses, biggest_win, biggest_loss
3. Fix any inconsistencies in the data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Game, Bet
from sqlalchemy import func

def recalculate_user_statistics():
    """Recalculate all user statistics from actual bet data"""
    print("🔧 Recalculating user statistics from actual bet data...")
    
    users = User.query.all()
    users_updated = 0
    
    for user in users:
        print(f"\n👤 Processing {user.username}...")
        
        # Get all bets for this user (excluding cancelled)
        user_bets = Bet.query.filter_by(user_id=user.id).filter(Bet.status != 'cancelled').all()
        
        # Initialize counters
        total_bets = len(user_bets)
        winning_bets = 0
        losing_bets = 0
        total_winnings = 0.0
        total_losses = 0.0
        biggest_win = 0.0
        biggest_loss = 0.0
        
        # Process each bet
        for bet in user_bets:
            if bet.status == 'won':
                winning_bets += 1
                total_winnings += bet.actual_payout
                net_win = bet.actual_payout - bet.wager_amount
                if net_win > biggest_win:
                    biggest_win = net_win
            elif bet.status == 'lost':
                losing_bets += 1
                total_losses += bet.wager_amount
                if bet.wager_amount > biggest_loss:
                    biggest_loss = bet.wager_amount
            # Note: 'push' and 'pending' don't count as wins or losses
        
        # Update user statistics
        old_stats = {
            'total_bets': user.total_bets,
            'winning_bets': user.winning_bets,
            'losing_bets': user.losing_bets,
            'total_winnings': user.total_winnings,
            'total_losses': user.total_losses,
            'biggest_win': user.biggest_win,
            'biggest_loss': user.biggest_loss
        }
        
        user.total_bets = total_bets
        user.winning_bets = winning_bets
        user.losing_bets = losing_bets
        user.total_winnings = total_winnings
        user.total_losses = total_losses
        user.biggest_win = biggest_win
        user.biggest_loss = biggest_loss
        
        # Show changes
        changes_made = False
        for key, old_value in old_stats.items():
            new_value = getattr(user, key)
            if old_value != new_value:
                print(f"  {key}: {old_value} → {new_value}")
                changes_made = True
        
        if changes_made:
            users_updated += 1
        else:
            print("  No changes needed")
        
        # Display current stats
        win_percentage = user.win_percentage
        print(f"  📊 Final stats: {total_bets} bets, {winning_bets} wins, {losing_bets} losses, {win_percentage:.1f}% win rate")
    
    db.session.commit()
    print(f"\n✅ Updated statistics for {users_updated} users")

def recalculate_user_balances():
    """Recalculate user balances from scratch based on bet history"""
    print("\n💰 Recalculating user balances from bet history...")
    
    users = User.query.all()
    users_updated = 0
    
    for user in users:
        # Start with starting balance
        calculated_balance = user.starting_balance
        
        # Get all bets in chronological order
        user_bets = Bet.query.filter_by(user_id=user.id).order_by(Bet.placed_at).all()
        
        for bet in user_bets:
            if bet.status == 'cancelled':
                # Cancelled bets should have been refunded
                continue
            elif bet.status == 'pending':
                # Pending bets have wager deducted
                calculated_balance -= bet.wager_amount
            elif bet.status == 'won':
                # Won bets: deduct wager, add payout
                calculated_balance = calculated_balance - bet.wager_amount + bet.actual_payout
            elif bet.status == 'lost':
                # Lost bets: wager already deducted when placed
                pass
            elif bet.status == 'push':
                # Push: wager was deducted when placed, but refunded
                pass
        
        # Check if balance needs updating
        if abs(calculated_balance - user.balance) > 0.01:  # Allow for small rounding differences
            print(f"  {user.username}: ${user.balance:.2f} → ${calculated_balance:.2f}")
            user.balance = calculated_balance
            users_updated += 1
    
    if users_updated > 0:
        db.session.commit()
        print(f"✅ Updated balances for {users_updated} users")
    else:
        print("✅ All user balances are correct")

def display_user_summary():
    """Display a summary of all users and their stats"""
    print("\n" + "="*80)
    print("📊 USER STATISTICS SUMMARY")
    print("="*80)
    
    users = User.query.order_by(User.total_bets.desc()).all()
    
    print(f"{'Username':<20} {'Bets':<6} {'Wins':<6} {'Losses':<6} {'Win%':<8} {'Balance':<12} {'P/L':<10}")
    print("-" * 80)
    
    for user in users:
        if user.total_bets > 0:  # Only show users with bets
            win_pct = user.win_percentage
            profit_loss = user.profit_loss
            
            print(f"{user.username:<20} {user.total_bets:<6} {user.winning_bets:<6} {user.losing_bets:<6} "
                  f"{win_pct:<7.1f}% ${user.balance:<11.0f} ${profit_loss:<9.0f}")

def check_specific_user(username="DevUser"):
    """Check a specific user's detailed bet history"""
    print(f"\n🔍 DETAILED CHECK FOR USER: {username}")
    print("="*60)
    
    user = User.query.filter_by(username=username).first()
    if not user:
        print(f"❌ User '{username}' not found!")
        return
    
    print(f"👤 User: {user.username}")
    print(f"💰 Balance: ${user.balance:.2f} (started with ${user.starting_balance:.2f})")
    print(f"📊 Stats: {user.total_bets} bets, {user.winning_bets} wins, {user.losing_bets} losses")
    print(f"🎯 Win Rate: {user.win_percentage:.1f}%")
    
    # Get all bets for this user
    user_bets = Bet.query.filter_by(user_id=user.id).order_by(Bet.placed_at.desc()).all()
    
    print(f"\n📋 BET HISTORY ({len(user_bets)} total bets):")
    print(f"{'Date':<12} {'Game':<30} {'Team':<20} {'Amount':<8} {'Status':<8} {'Payout':<8}")
    print("-" * 90)
    
    for bet in user_bets[:10]:  # Show last 10 bets
        game_info = f"{bet.game.away_team_abbr or bet.game.away_team[:3]} @ {bet.game.home_team_abbr or bet.game.home_team[:3]}"
        team = bet.team_picked[:15] if bet.team_picked else "Unknown"
        date = bet.placed_at.strftime("%m/%d")
        
        print(f"{date:<12} {game_info:<30} {team:<20} ${bet.wager_amount:<7.0f} "
              f"{bet.status:<8} ${bet.actual_payout:<7.0f}")
    
    if len(user_bets) > 10:
        print(f"... and {len(user_bets) - 10} more bets")

def main():
    """Main function to fix all user statistics"""
    app = create_app()
    
    with app.app_context():
        print("🔧 USER STATISTICS REPAIR TOOL")
        print("="*50)
        print("This will recalculate all user statistics from actual bet data")
        print("")
        
        # Check specific user first
        check_specific_user("DevUser")
        
        # Recalculate statistics
        recalculate_user_statistics()
        
        # Recalculate balances
        recalculate_user_balances()
        
        # Show updated summary
        display_user_summary()
        
        # Check specific user again
        print("\n" + "="*60)
        print("AFTER FIXES:")
        check_specific_user("DevUser")
        
        print("\n✅ USER STATISTICS REPAIR COMPLETE!")
        print("🎯 All user stats should now be accurate based on actual bet history")

if __name__ == '__main__':
    main()