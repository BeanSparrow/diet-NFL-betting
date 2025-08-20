#!/usr/bin/env python3
"""
Comprehensive test data script:
1. Spoof Week 1 game results with realistic NFL scores
2. Resolve all existing Week 1 bets
3. Generate additional bets for Weeks 2 and 3 (50+ each)
4. Update user statistics
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Game, Bet
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import random
import string

def generate_realistic_nfl_score():
    """Generate realistic NFL scores"""
    # Common NFL score patterns
    score_patterns = [
        # Close games (3-7 point differences)
        (24, 21), (17, 14), (20, 17), (27, 24), (31, 28), (13, 10),
        # Medium spreads (8-14 points)
        (28, 17), (24, 10), (31, 17), (21, 7), (35, 21), (27, 13),
        # Blowouts (15+ points)
        (35, 14), (42, 17), (31, 10), (38, 14), (45, 17), (28, 3),
        # Defensive games (low scoring)
        (16, 13), (19, 16), (12, 9), (15, 12), (10, 7), (13, 6),
        # High scoring
        (45, 38), (52, 35), (49, 42), (38, 35), (41, 38)
    ]
    
    base_score = random.choice(score_patterns)
    # Add some variation
    home_score = base_score[0] + random.randint(-3, 3)
    away_score = base_score[1] + random.randint(-3, 3)
    
    # Ensure no negative scores
    home_score = max(0, home_score)
    away_score = max(0, away_score)
    
    return home_score, away_score

def spoof_week1_results():
    """Add realistic results to all Week 1 games"""
    print("🏈 Spoofing Week 1 game results...")
    
    week1_games = Game.query.filter_by(week=1).all()
    
    if not week1_games:
        print("❌ No Week 1 games found!")
        return False
    
    results_added = 0
    
    for game in week1_games:
        if game.status != 'final':
            home_score, away_score = generate_realistic_nfl_score()
            
            # Update game with results
            game.home_score = home_score
            game.away_score = away_score
            game.status = 'final'
            
            # Determine winner
            if home_score > away_score:
                game.winner = game.home_team
                game.is_tie = False
            elif away_score > home_score:
                game.winner = game.away_team
                game.is_tie = False
            else:
                game.winner = None
                game.is_tie = True
            
            results_added += 1
            
            print(f"  {game.away_team} {away_score} @ {game.home_team} {home_score} - Winner: {game.winner or 'TIE'}")
    
    db.session.commit()
    print(f"✅ Added results to {results_added} Week 1 games")
    return True

def resolve_week1_bets():
    """Resolve all pending bets on Week 1 games"""
    print("💰 Resolving Week 1 bets...")
    
    # Get all pending bets on Week 1 games
    week1_bets = db.session.query(Bet).join(Game).filter(
        Game.week == 1,
        Bet.status == 'pending'
    ).all()
    
    if not week1_bets:
        print("❌ No pending Week 1 bets found!")
        return
    
    bets_resolved = 0
    total_payouts = 0.0
    
    for bet in week1_bets:
        game = bet.game
        user = bet.user
        
        # Resolve the bet based on game outcome
        if game.is_tie:
            # Push - return original wager
            bet.status = 'push'
            bet.actual_payout = bet.wager_amount
            user.balance += bet.wager_amount  # Return wager
        elif bet.team_picked == game.winner:
            # Win
            bet.status = 'won'
            bet.actual_payout = bet.potential_payout
            user.balance += bet.potential_payout
            user.winning_bets += 1
            user.total_winnings += bet.actual_payout
            
            # Track biggest win
            net_win = bet.actual_payout - bet.wager_amount
            if net_win > user.biggest_win:
                user.biggest_win = net_win
        else:
            # Loss
            bet.status = 'lost'
            bet.actual_payout = 0.0
            user.losing_bets += 1
            user.total_losses += bet.wager_amount
            
            # Track biggest loss
            if bet.wager_amount > user.biggest_loss:
                user.biggest_loss = bet.wager_amount
        
        bet.settled_at = datetime.now(timezone.utc)
        bets_resolved += 1
        total_payouts += bet.actual_payout
        
        print(f"  {user.username}: {bet.team_picked} ${bet.wager_amount} -> {bet.status.upper()} (${bet.actual_payout})")
    
    db.session.commit()
    print(f"✅ Resolved {bets_resolved} bets, total payouts: ${total_payouts:.2f}")

def create_games_for_week(week_num, num_games=16):
    """Create games for a specific week if they don't exist"""
    existing_games = Game.query.filter_by(week=week_num).count()
    
    if existing_games >= num_games:
        print(f"Week {week_num} already has {existing_games} games")
        return Game.query.filter_by(week=week_num).all()
    
    print(f"Creating {num_games - existing_games} additional games for Week {week_num}...")
    
    # NFL team names for realistic games
    nfl_teams = [
        ('Arizona Cardinals', 'ARI'), ('Atlanta Falcons', 'ATL'), ('Baltimore Ravens', 'BAL'),
        ('Buffalo Bills', 'BUF'), ('Carolina Panthers', 'CAR'), ('Chicago Bears', 'CHI'),
        ('Cincinnati Bengals', 'CIN'), ('Cleveland Browns', 'CLE'), ('Dallas Cowboys', 'DAL'),
        ('Denver Broncos', 'DEN'), ('Detroit Lions', 'DET'), ('Green Bay Packers', 'GB'),
        ('Houston Texans', 'HOU'), ('Indianapolis Colts', 'IND'), ('Jacksonville Jaguars', 'JAX'),
        ('Kansas City Chiefs', 'KC'), ('Las Vegas Raiders', 'LV'), ('Los Angeles Chargers', 'LAC'),
        ('Los Angeles Rams', 'LAR'), ('Miami Dolphins', 'MIA'), ('Minnesota Vikings', 'MIN'),
        ('New England Patriots', 'NE'), ('New Orleans Saints', 'NO'), ('New York Giants', 'NYG'),
        ('New York Jets', 'NYJ'), ('Philadelphia Eagles', 'PHI'), ('Pittsburgh Steelers', 'PIT'),
        ('San Francisco 49ers', 'SF'), ('Seattle Seahawks', 'SEA'), ('Tampa Bay Buccaneers', 'TB'),
        ('Tennessee Titans', 'TEN'), ('Washington Commanders', 'WAS')
    ]
    
    # Calculate game time (spread across Sunday)
    base_date = datetime.now(timezone.utc).replace(hour=18, minute=0, second=0, microsecond=0)
    base_date += timedelta(days=(6 - base_date.weekday()) % 7)  # Next Sunday
    base_date += timedelta(weeks=week_num - 1)  # Adjust for week
    
    games_created = 0
    
    for i in range(existing_games, num_games):
        # Pick random teams
        away_team, away_abbr = random.choice(nfl_teams)
        home_team, home_abbr = random.choice(nfl_teams)
        
        # Ensure different teams
        while home_team == away_team:
            home_team, home_abbr = random.choice(nfl_teams)
        
        # Vary game times
        game_time = base_date + timedelta(hours=random.choice([0, 3, 6]))  # 1pm, 4pm, 7pm games
        
        game = Game(
            espn_game_id=f"test_week{week_num}_game{i+1}_{random.randint(1000, 9999)}",
            week=week_num,
            season=2024,
            home_team=home_team,
            home_team_abbr=home_abbr,
            away_team=away_team,
            away_team_abbr=away_abbr,
            game_time=game_time,
            status='scheduled',
            total_bets=0,
            total_wagered=0.0,
            home_bets=0,
            away_bets=0,
            home_wagered=0.0,
            away_wagered=0.0
        )
        
        db.session.add(game)
        games_created += 1
    
    if games_created > 0:
        db.session.commit()
        print(f"✅ Created {games_created} games for Week {week_num}")
    
    return Game.query.filter_by(week=week_num).all()

def generate_bets_for_week(week_num, target_bets=60):
    """Generate bets for a specific week"""
    print(f"🎲 Generating ~{target_bets} bets for Week {week_num}...")
    
    # Get all users
    users = User.query.filter(User.discord_id.like('test_%')).all()
    if not users:
        print("❌ No test users found!")
        return []
    
    # Get games for this week
    games = create_games_for_week(week_num)
    if not games:
        print(f"❌ No games found for Week {week_num}!")
        return []
    
    # Create game popularity weights
    game_popularity = {}
    for game in games:
        popularity = random.choice([0.5, 0.8, 1.0, 1.2, 1.5, 2.0])
        game_popularity[game.id] = popularity
    
    # Normalize popularity
    total_pop = sum(game_popularity.values())
    for game_id in game_popularity:
        game_popularity[game_id] /= total_pop
    
    bets_created = []
    
    for i in range(target_bets):
        # Select user (some users more active)
        user_weights = [1.0 if random.random() > 0.3 else 2.5 for u in users]
        user = random.choices(users, weights=user_weights, k=1)[0]
        
        # Select game based on popularity
        game = random.choices(
            games,
            weights=[game_popularity[g.id] for g in games],
            k=1
        )[0]
        
        # Check if user already has a pending bet on this game
        existing_bet = Bet.query.filter_by(
            user_id=user.id,
            game_id=game.id,
            status='pending'
        ).first()
        
        if existing_bet:
            continue  # Skip if user already bet on this game
        
        # Determine bet amount
        bet_amounts = [
            5, 10, 10, 15, 20, 25, 25, 25, 30, 50, 50, 50, 75, 
            100, 100, 100, 150, 200, 250, 300, 500
        ]
        
        # Limit to user's balance
        available_amounts = [amt for amt in bet_amounts if amt <= user.balance]
        if not available_amounts:
            continue
        
        wager_amount = random.choice(available_amounts)
        
        # Pick team (slight home field advantage)
        if random.random() < 0.52:  # 52% pick home team
            team_picked = game.home_team
        else:
            team_picked = game.away_team
        
        # Create bet
        bet = Bet(
            user_id=user.id,
            game_id=game.id,
            team_picked=team_picked,
            wager_amount=wager_amount,
            potential_payout=wager_amount * 2.0,
            actual_payout=0.0,
            status='pending',
            placed_at=datetime.now(timezone.utc)
        )
        
        # Update user balance and stats
        user.balance -= wager_amount
        user.total_bets += 1
        
        # Update game stats
        game.total_bets += 1
        game.total_wagered += wager_amount
        
        if team_picked == game.home_team:
            game.home_bets += 1
            game.home_wagered += wager_amount
        else:
            game.away_bets += 1
            game.away_wagered += wager_amount
        
        db.session.add(bet)
        bets_created.append(bet)
    
    db.session.commit()
    print(f"✅ Created {len(bets_created)} bets for Week {week_num}")
    
    return bets_created

def print_final_statistics():
    """Print comprehensive statistics about the test data"""
    print("\n" + "="*50)
    print("📊 FINAL TEST DATA STATISTICS")
    print("="*50)
    
    # User stats
    total_users = User.query.filter(User.discord_id.like('test_%')).count()
    print(f"\n👥 USERS:")
    print(f"  Total test users: {total_users}")
    
    # Bet stats by week
    print(f"\n🎯 BETS BY WEEK:")
    for week in [1, 2, 3]:
        week_bets = db.session.query(Bet).join(Game).filter(Game.week == week).count()
        pending_bets = db.session.query(Bet).join(Game).filter(Game.week == week, Bet.status == 'pending').count()
        resolved_bets = db.session.query(Bet).join(Game).filter(Game.week == week, Bet.status != 'pending').count()
        
        print(f"  Week {week}: {week_bets} total ({resolved_bets} resolved, {pending_bets} pending)")
    
    # Overall betting stats
    total_bets = db.session.query(Bet).join(User).filter(User.discord_id.like('test_%')).count()
    total_wagered = db.session.query(func.sum(Bet.wager_amount)).join(User).filter(
        User.discord_id.like('test_%'), Bet.status != 'cancelled'
    ).scalar() or 0
    
    print(f"\n💰 OVERALL BETTING:")
    print(f"  Total bets: {total_bets}")
    print(f"  Total wagered: ${total_wagered:,.2f}")
    
    # Bet status breakdown
    print(f"\n📈 BET STATUS BREAKDOWN:")
    for status in ['pending', 'won', 'lost', 'push', 'cancelled']:
        count = db.session.query(Bet).join(User).filter(
            User.discord_id.like('test_%'), Bet.status == status
        ).count()
        if count > 0:
            print(f"  {status.title()}: {count} bets")
    
    # Game stats by week
    print(f"\n🏈 GAMES BY WEEK:")
    for week in [1, 2, 3]:
        week_games = Game.query.filter_by(week=week).count()
        games_with_bets = Game.query.filter(Game.week == week, Game.total_bets > 0).count()
        
        print(f"  Week {week}: {week_games} games ({games_with_bets} with bets)")
    
    # Top bettors
    print(f"\n🎲 TOP BETTORS:")
    top_users = User.query.filter(User.discord_id.like('test_%'))\
                         .order_by(User.total_bets.desc()).limit(5).all()
    
    for i, user in enumerate(top_users, 1):
        print(f"  {i}. {user.username}: {user.total_bets} bets, ${user.balance:,.0f} balance")

def main():
    """Main function"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Starting comprehensive test data generation...")
        print("This will:")
        print("  1. Add realistic results to Week 1 games")
        print("  2. Resolve all existing Week 1 bets")
        print("  3. Generate 60+ bets for Week 2")
        print("  4. Generate 60+ bets for Week 3")
        print("")
        
        # Step 1: Spoof Week 1 results
        if not spoof_week1_results():
            return
        
        # Step 2: Resolve Week 1 bets
        resolve_week1_bets()
        
        # Step 3: Generate Week 2 bets
        generate_bets_for_week(2, 65)
        
        # Step 4: Generate Week 3 bets  
        generate_bets_for_week(3, 70)
        
        # Step 5: Print final statistics
        print_final_statistics()
        
        print(f"\n✅ COMPLETE! Your betting community now has:")
        print(f"   • Realistic Week 1 results with resolved bets")
        print(f"   • 60+ additional bets on Week 2 games")
        print(f"   • 70+ additional bets on Week 3 games")
        print(f"   • Rich data to test all accolades and analytics!")

if __name__ == '__main__':
    main()