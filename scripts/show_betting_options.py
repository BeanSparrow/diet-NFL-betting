#!/usr/bin/env python3
"""
Show Available Betting Options

Quick overview of what's available for testing
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Game, User, Bet

def main():
    app = create_app('development')
    
    with app.app_context():
        print("NFL Betting System - Available Options")
        print("=" * 50)
        
        # Show upcoming games by category
        now = datetime.now()
        
        # Preseason games
        preseason_games = Game.query.filter(
            Game.season_type == 'preseason',
            Game.status == 'scheduled',
            Game.game_time > now
        ).order_by(Game.game_time).all()
        
        print(f"\nPRESEASON WEEK 4 GAMES ({len(preseason_games)} available)")
        print("=" * 45)
        for i, game in enumerate(preseason_games[:8], 1):  # Show first 8
            time_str = game.game_time.strftime('%m/%d %H:%M')
            print(f"{i:2}. {game.away_team} @ {game.home_team} - {time_str}")
        if len(preseason_games) > 8:
            print(f"    ... and {len(preseason_games) - 8} more")
        
        # Regular season games
        regular_games = Game.query.filter(
            Game.season_type == 'regular',
            Game.status == 'scheduled',
            Game.game_time > now
        ).order_by(Game.game_time).all()
        
        print(f"\nREGULAR SEASON GAMES ({len(regular_games)} available)")
        print("=" * 40)
        
        # Group by week
        week_games = {}
        for game in regular_games:
            if game.week not in week_games:
                week_games[game.week] = []
            week_games[game.week].append(game)
        
        for week in sorted(week_games.keys()):
            games = week_games[week]
            print(f"\nWeek {week} ({len(games)} games):")
            for i, game in enumerate(games[:5], 1):  # Show first 5 per week
                time_str = game.game_time.strftime('%m/%d %H:%M')
                print(f"  {i}. {game.away_team} @ {game.home_team} - {time_str}")
            if len(games) > 5:
                print(f"      ... and {len(games) - 5} more")
        
        # Show user betting stats
        users_with_balance = User.query.filter(User.balance > 100).order_by(User.balance.desc()).all()
        
        print(f"\nUSERS READY TO BET ({len(users_with_balance)} with sufficient balance)")
        print("=" * 55)
        for user in users_with_balance[:8]:  # Show top 8
            pending_bets = Bet.query.filter_by(user_id=user.id, status='pending').count()
            print(f"  {user.username:<15} - ${user.balance:>8.2f} ({pending_bets} pending bets)")
        
        # Show recent activity
        recent_bets = Bet.query.filter(
            Bet.status.in_(['won', 'lost', 'push'])
        ).order_by(Bet.settled_at.desc()).limit(5).all()
        
        print(f"\nRECENT SETTLEMENTS")
        print("=" * 25)
        for bet in recent_bets:
            result_symbol = "WIN" if bet.status == 'won' else "LOSS" if bet.status == 'lost' else "PUSH"
            payout = f"${bet.actual_payout:.0f}" if bet.actual_payout > 0 else "$0"
            print(f"  {result_symbol} {bet.user.username} - {bet.team_picked} ({bet.status}) - {payout}")
        
        print(f"\nQUICK START OPTIONS")
        print("=" * 25)
        print("1. Run automated simulation:")
        print("   ./venv/Scripts/python.exe scripts/simulate_betting.py")
        print("")
        print("2. Manual betting control:")
        print("   ./venv/Scripts/python.exe scripts/manual_betting.py")
        print("")
        print("3. View leaderboard:")
        print("   http://127.0.0.1:5000/stats/leaderboard")
        print("")
        print("4. Add more games:")
        print("   ./venv/Scripts/python.exe scripts/add_upcoming_games.py")

if __name__ == '__main__':
    main()