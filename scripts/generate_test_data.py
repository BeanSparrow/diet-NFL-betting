#!/usr/bin/env python3
"""
Generate test users and bets for Week 1 games
Creates 20+ users and 100+ bets with realistic distributions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Game, Bet
from datetime import datetime, timezone
import random
import string

def generate_username():
    """Generate a realistic username"""
    prefixes = ['Cool', 'Super', 'Pro', 'Epic', 'Mega', 'Ultra', 'Ninja', 'Dragon', 'Shadow', 'Thunder']
    suffixes = ['Gamer', 'Player', 'Master', 'Lord', 'King', 'Wizard', 'Knight', 'Warrior', 'Champion', 'Legend']
    numbers = [''.join(random.choices(string.digits, k=random.randint(2, 4))) for _ in range(5)]
    
    username = random.choice(prefixes) + random.choice(suffixes) + random.choice(numbers + [''])
    return username

def create_test_users(num_users=25):
    """Create test users with varying balances"""
    users = []
    
    print(f"Creating {num_users} test users...")
    
    for i in range(num_users):
        # Generate unique Discord ID
        discord_id = f"test_{i+1000}_{random.randint(1000, 9999)}"
        
        # Check if user already exists
        existing_user = User.query.filter_by(discord_id=discord_id).first()
        if existing_user:
            users.append(existing_user)
            continue
        
        # Create user with varying starting balances
        balance_options = [10000, 10000, 10000, 15000, 20000]  # Most users start with 10k
        starting_balance = random.choice(balance_options)
        
        # Some users have already won/lost money
        balance_variance = random.uniform(0.5, 1.5)
        current_balance = starting_balance * balance_variance
        
        user = User(
            discord_id=discord_id,
            username=generate_username(),
            discriminator=str(random.randint(1000, 9999)),
            balance=current_balance,
            starting_balance=starting_balance,
            total_bets=0,
            winning_bets=0,
            losing_bets=0,
            is_admin=False
        )
        
        db.session.add(user)
        users.append(user)
    
    db.session.commit()
    print(f"Created {len(users)} users")
    return users

def create_test_bets(users, num_bets=120):
    """Create test bets on Week 1 games with realistic distribution"""
    
    # Get Week 1 games that are bettable
    week1_games = Game.query.filter_by(week=1).all()
    
    if not week1_games:
        print("No Week 1 games found! Please add games first.")
        return []
    
    print(f"Found {len(week1_games)} Week 1 games")
    
    bets_created = []
    
    # Create betting patterns - some games are more popular
    game_popularity = {}
    for game in week1_games:
        # Random popularity weight (some games get more action)
        popularity = random.choice([0.5, 1.0, 1.0, 1.5, 2.0])
        game_popularity[game.id] = popularity
    
    # Normalize popularity to sum to 1
    total_pop = sum(game_popularity.values())
    for game_id in game_popularity:
        game_popularity[game_id] /= total_pop
    
    print(f"Creating {num_bets} bets...")
    
    for i in range(num_bets):
        # Select user (some users bet more than others)
        user_weights = [1.0 if random.random() > 0.3 else 2.0 for u in users]
        user = random.choices(users, weights=user_weights, k=1)[0]
        
        # Select game based on popularity
        game = random.choices(
            week1_games, 
            weights=[game_popularity[g.id] for g in week1_games],
            k=1
        )[0]
        
        # Check if user already has a bet on this game
        existing_bet = Bet.query.filter_by(
            user_id=user.id,
            game_id=game.id,
            status='pending'
        ).first()
        
        if existing_bet:
            continue  # Skip if user already bet on this game
        
        # Determine bet amount with realistic distribution
        bet_amounts = [
            5, 10, 10, 20, 25, 25, 25, 50, 50, 50, 50, 
            75, 100, 100, 100, 100, 150, 200, 250, 500
        ]
        
        # Limit bet to user's balance
        available_amounts = [amt for amt in bet_amounts if amt <= user.balance]
        if not available_amounts:
            continue  # User doesn't have enough balance
        
        wager_amount = random.choice(available_amounts)
        
        # Pick team with some bias (home teams slightly favored)
        if random.random() < 0.55:  # 55% pick home team
            team_picked = game.home_team
        else:
            team_picked = game.away_team
        
        # Create the bet
        bet = Bet(
            user_id=user.id,
            game_id=game.id,
            team_picked=team_picked,
            wager_amount=wager_amount,
            potential_payout=wager_amount * 2.0,  # 2x payout
            actual_payout=0.0,
            status='pending',
            placed_at=datetime.now(timezone.utc)
        )
        
        # Update user balance
        user.balance -= wager_amount
        user.total_bets += 1
        
        # Update game statistics
        game.total_bets += 1
        game.total_wagered += wager_amount
        
        if team_picked == game.home_team:
            game.home_bets += 1
            game.home_wagered = (game.home_wagered or 0) + wager_amount
        else:
            game.away_bets += 1
            game.away_wagered = (game.away_wagered or 0) + wager_amount
        
        db.session.add(bet)
        bets_created.append(bet)
    
    db.session.commit()
    print(f"Created {len(bets_created)} bets")
    
    return bets_created

def print_statistics():
    """Print statistics about the generated data"""
    print("\n=== Test Data Statistics ===")
    
    # User stats
    total_users = User.query.filter(User.discord_id.like('test_%')).count()
    print(f"Total test users: {total_users}")
    
    # Bet stats
    total_bets = Bet.query.join(User).filter(User.discord_id.like('test_%')).count()
    print(f"Total test bets: {total_bets}")
    
    # Game stats
    print("\n=== Week 1 Game Statistics ===")
    week1_games = Game.query.filter_by(week=1).filter(Game.total_bets > 0).all()
    
    for game in week1_games:
        print(f"\n{game.away_team} @ {game.home_team}")
        print(f"  Total bets: {game.total_bets}")
        print(f"  Total wagered: ${game.total_wagered:.2f}")
        print(f"  Away: {game.away_bets} bets (${game.away_wagered or 0:.2f}) - {game.away_bet_percentage:.1f}%")
        print(f"  Home: {game.home_bets} bets (${game.home_wagered or 0:.2f}) - {game.home_bet_percentage:.1f}%")
        
        # Money distribution
        if game.total_wagered > 0:
            away_money_pct = (game.away_wagered or 0) / game.total_wagered * 100
            home_money_pct = (game.home_wagered or 0) / game.total_wagered * 100
            print(f"  Money split: Away {away_money_pct:.1f}% / Home {home_money_pct:.1f}%")

def main():
    """Main function to generate test data"""
    app = create_app()
    
    with app.app_context():
        print("Starting test data generation...")
        
        # Check if we have Week 1 games
        week1_games = Game.query.filter_by(week=1).all()
        if not week1_games:
            print("\n❌ No Week 1 games found in database!")
            print("Please add Week 1 games first using the admin panel or game import script.")
            return
        
        print(f"Found {len(week1_games)} Week 1 games")
        
        # Create test users
        users = create_test_users(25)  # Create 25 users
        
        # Create test bets
        bets = create_test_bets(users, 120)  # Try to create 120 bets
        
        # Print statistics
        print_statistics()
        
        print("\n✅ Test data generation complete!")
        print("You can now view the betting statistics and Community Activity visualizations.")

if __name__ == '__main__':
    main()