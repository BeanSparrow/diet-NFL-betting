#!/usr/bin/env python3
"""
Add Upcoming Games for Testing

This script adds upcoming preseason games and future regular season games
for testing the betting system.
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Game

def add_preseason_week_4_games():
    """Add Week 4 preseason games (final preseason week)"""
    print("Adding Week 4 Preseason Games...")
    
    # Week 4 preseason matchups (these are typically Thursday-Saturday)
    week_4_games = [
        ("Detroit Lions", "DET", "Pittsburgh Steelers", "PIT"),
        ("Atlanta Falcons", "ATL", "Jacksonville Jaguars", "JAX"), 
        ("Buffalo Bills", "BUF", "Carolina Panthers", "CAR"),
        ("Chicago Bears", "CHI", "Kansas City Chiefs", "KC"),
        ("Cleveland Browns", "CLE", "Seattle Seahawks", "SEA"),
        ("Dallas Cowboys", "DAL", "Los Angeles Chargers", "LAC"),
        ("Denver Broncos", "DEN", "Arizona Cardinals", "ARI"),
        ("Green Bay Packers", "GB", "Baltimore Ravens", "BAL"),
        ("Houston Texans", "HOU", "New Orleans Saints", "NO"),
        ("Indianapolis Colts", "IND", "Cincinnati Bengals", "CIN"),
        ("Las Vegas Raiders", "LV", "San Francisco 49ers", "SF"),
        ("Miami Dolphins", "MIA", "Tampa Bay Buccaneers", "TB"),
        ("Minnesota Vikings", "MIN", "Philadelphia Eagles", "PHI"),
        ("New England Patriots", "NE", "Washington Commanders", "WAS"),
        ("New York Giants", "NYG", "New York Jets", "NYJ"),
        ("Tennessee Titans", "TEN", "Los Angeles Rams", "LAR")
    ]
    
    # Start games from tomorrow evening
    base_time = datetime.now() + timedelta(days=1, hours=19)  # Tomorrow at 7 PM
    
    games_added = []
    for i, (home_team, home_abbr, away_team, away_abbr) in enumerate(week_4_games):
        # Spread games across Thursday-Saturday
        game_time = base_time + timedelta(days=i//6, hours=(i%6)*2)  # 6 games per day, 2 hours apart
        
        game = Game(
            espn_game_id=f"2024_pre_4_{i:02d}",
            week=4,
            season=2024,
            season_type='preseason',
            home_team=home_team,
            home_team_abbr=home_abbr,
            away_team=away_team,
            away_team_abbr=away_abbr,
            game_time=game_time,
            status='scheduled',
            home_score=0,
            away_score=0,
            total_bets=0,
            total_wagered=0.0
        )
        
        db.session.add(game)
        games_added.append(game)
        print(f"  Added: {away_team} @ {home_team} - {game_time.strftime('%Y-%m-%d %H:%M')}")
    
    return games_added

def add_regular_season_week_1_games():
    """Add Week 1 regular season games"""
    print("\nAdding Week 1 Regular Season Games...")
    
    # Week 1 regular season matchups 
    week_1_games = [
        ("Kansas City Chiefs", "KC", "Detroit Lions", "DET"),       # Thursday Night
        ("Atlanta Falcons", "ATL", "Pittsburgh Steelers", "PIT"),   # Sunday 1 PM
        ("Arizona Cardinals", "ARI", "Buffalo Bills", "BUF"),       # Sunday 1 PM
        ("Cincinnati Bengals", "CIN", "New England Patriots", "NE"), # Sunday 1 PM
        ("Houston Texans", "HOU", "Indianapolis Colts", "IND"),     # Sunday 1 PM
        ("Jacksonville Jaguars", "JAX", "Miami Dolphins", "MIA"),   # Sunday 1 PM
        ("Minnesota Vikings", "MIN", "New York Giants", "NYG"),     # Sunday 1 PM
        ("Philadelphia Eagles", "PHI", "Green Bay Packers", "GB"),  # Sunday 1 PM
        ("Tennessee Titans", "TEN", "Chicago Bears", "CHI"),        # Sunday 1 PM
        ("Cleveland Browns", "CLE", "Dallas Cowboys", "DAL"),       # Sunday 4:25 PM
        ("Denver Broncos", "DEN", "Seattle Seahawks", "SEA"),       # Sunday 4:25 PM
        ("Las Vegas Raiders", "LV", "Los Angeles Chargers", "LAC"), # Sunday 4:25 PM
        ("Tampa Bay Buccaneers", "TB", "Washington Commanders", "WAS"), # Sunday 4:25 PM
        ("San Francisco 49ers", "SF", "New York Jets", "NYJ"),      # Monday Night
        ("New Orleans Saints", "NO", "Carolina Panthers", "CAR"),   # Sunday 1 PM
        ("Baltimore Ravens", "BAL", "Los Angeles Rams", "LAR")      # Sunday 8:20 PM
    ]
    
    # Start regular season games 1 week after preseason ends
    base_time = datetime.now() + timedelta(days=8, hours=20)  # Next week Thursday at 8 PM
    
    games_added = []
    for i, (home_team, home_abbr, away_team, away_abbr) in enumerate(week_1_games):
        if i == 0:  # Thursday Night
            game_time = base_time
        elif i <= 8:  # Early Sunday games (1 PM ET)
            game_time = base_time + timedelta(days=3, hours=17)  # Sunday 1 PM
            game_time += timedelta(minutes=i*15)  # Stagger slightly for realism
        elif i <= 12:  # Late Sunday games (4:25 PM ET)
            game_time = base_time + timedelta(days=3, hours=20, minutes=25)  # Sunday 4:25 PM
            game_time += timedelta(minutes=(i-9)*15)
        elif i == 13:  # Monday Night
            game_time = base_time + timedelta(days=4, hours=20)  # Monday 8 PM
        elif i == 14:  # Sunday 1 PM
            game_time = base_time + timedelta(days=3, hours=17, minutes=14*15)
        else:  # Sunday Night
            game_time = base_time + timedelta(days=4, hours=0, minutes=20)  # Sunday 8:20 PM
        
        game = Game(
            espn_game_id=f"2024_reg_1_{i:02d}",
            week=1,
            season=2024,
            season_type='regular',
            home_team=home_team,
            home_team_abbr=home_abbr,
            away_team=away_team,
            away_team_abbr=away_abbr,
            game_time=game_time,
            status='scheduled',
            home_score=0,
            away_score=0,
            total_bets=0,
            total_wagered=0.0
        )
        
        db.session.add(game)
        games_added.append(game)
        print(f"  Added: {away_team} @ {home_team} - {game_time.strftime('%Y-%m-%d %H:%M')}")
    
    return games_added

def add_extra_test_games():
    """Add some extra test games spread out over time"""
    print("\nAdding Extra Test Games for Extended Testing...")
    
    # Additional test matchups
    test_games = [
        ("Miami Dolphins", "MIA", "Buffalo Bills", "BUF"),
        ("Dallas Cowboys", "DAL", "Philadelphia Eagles", "PHI"),
        ("Green Bay Packers", "GB", "Chicago Bears", "CHI"),
        ("Kansas City Chiefs", "KC", "Las Vegas Raiders", "LV"),
        ("San Francisco 49ers", "SF", "Seattle Seahawks", "SEA"),
        ("Tampa Bay Buccaneers", "TB", "New Orleans Saints", "NO")
    ]
    
    # Spread these over the next 2 weeks
    base_time = datetime.now() + timedelta(days=14, hours=13)  # 2 weeks from now
    
    games_added = []
    for i, (home_team, home_abbr, away_team, away_abbr) in enumerate(test_games):
        game_time = base_time + timedelta(days=i*2, hours=i*3)  # Spread across different days/times
        
        game = Game(
            espn_game_id=f"2024_test_{i:02d}",
            week=2,
            season=2024,
            season_type='regular',
            home_team=home_team,
            home_team_abbr=home_abbr,
            away_team=away_team,
            away_team_abbr=away_abbr,
            game_time=game_time,
            status='scheduled',
            home_score=0,
            away_score=0,
            total_bets=0,
            total_wagered=0.0
        )
        
        db.session.add(game)
        games_added.append(game)
        print(f"  Added: {away_team} @ {home_team} - {game_time.strftime('%Y-%m-%d %H:%M')}")
    
    return games_added

def update_existing_games():
    """Update existing games to correct season type"""
    print("\nUpdating existing games to preseason...")
    
    existing_games = Game.query.filter_by(season_type='regular').all()
    updated_count = 0
    
    for game in existing_games:
        game.season_type = 'preseason'
        game.week = 3  # Make them week 3 preseason
        updated_count += 1
    
    print(f"  Updated {updated_count} existing games to preseason week 3")
    return updated_count

def main():
    """Add upcoming games for testing"""
    app = create_app('development')
    
    with app.app_context():
        print("Adding Upcoming Games for Testing")
        print("=" * 50)
        
        # Update existing games
        update_existing_games()
        
        # Add new upcoming games
        preseason_games = add_preseason_week_4_games()
        regular_games = add_regular_season_week_1_games()
        test_games = add_extra_test_games()
        
        # Commit all changes
        db.session.commit()
        
        total_added = len(preseason_games) + len(regular_games) + len(test_games)
        
        print(f"\nSUCCESS: Added {total_added} new games!")
        print(f"  - {len(preseason_games)} Preseason Week 4 games")
        print(f"  - {len(regular_games)} Regular Season Week 1 games") 
        print(f"  - {len(test_games)} Extra test games")
        
        # Show summary
        scheduled_count = Game.query.filter_by(status='scheduled').count()
        total_count = Game.query.count()
        
        print(f"\nDatabase Summary:")
        print(f"  - Total games: {total_count}")
        print(f"  - Scheduled games: {scheduled_count}")
        print(f"  - Final games: {total_count - scheduled_count}")
        
        print(f"\nYou can now:")
        print("  1. Run simulate_betting.py to place bets on upcoming games")
        print("  2. Use manual_betting.py for precise control")
        print("  3. View available games in the web app")

if __name__ == '__main__':
    main()