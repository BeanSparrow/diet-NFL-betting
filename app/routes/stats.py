from flask import render_template, request, jsonify
from app.auth_decorators import login_required
from app.routes import stats_bp
from app.models import User, Game, Bet, get_current_user
from app import db
from sqlalchemy import func, desc, and_, extract
from typing import List, Dict, Any
from datetime import datetime, timezone

def get_leaderboard_rankings(sort_by: str = 'balance', limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get leaderboard rankings with comprehensive user statistics
    
    Args:
        sort_by: Sorting criteria ('balance', 'profit', 'win_rate')
        limit: Maximum number of users to return
        
    Returns:
        List of user ranking dictionaries with all stats
    """
    query = User.query
    
    # Apply sorting based on criteria
    if sort_by == 'balance':
        users = query.order_by(desc(User.balance)).limit(limit).all()
    elif sort_by == 'profit':
        users = query.order_by(desc(User.balance - User.starting_balance)).limit(limit).all()
    elif sort_by == 'win_rate':
        # Only include users with bets for win rate ranking
        users = query.filter(User.total_bets > 0)\
            .order_by(desc(User.winning_bets * 100.0 / User.total_bets)).limit(limit).all()
    else:
        # Default to balance
        users = query.order_by(desc(User.balance)).limit(limit).all()
    
    # Build ranking list with comprehensive stats
    rankings = []
    for rank, user in enumerate(users, 1):
        rankings.append({
            'rank': rank,
            'username': user.username,
            'discord_id': user.discord_id,
            'balance': user.balance,
            'starting_balance': user.starting_balance,
            'profit_loss': user.profit_loss,
            'total_bets': user.total_bets,
            'winning_bets': user.winning_bets,
            'losing_bets': user.losing_bets,
            'win_percentage': user.win_percentage,
            'total_winnings': user.total_winnings,
            'total_losses': user.total_losses,
            'biggest_win': user.biggest_win,
            'biggest_loss': user.biggest_loss
        })
    
    return rankings


@stats_bp.route('/leaderboard')
def leaderboard():
    """Display community leaderboard with graceful degradation"""
    sort_by = request.args.get('sort', 'balance')
    limit = request.args.get('limit', 50, type=int)
    rankings = []
    total_users = 0
    
    try:
        # Get rankings using the new function with error handling
        rankings = get_leaderboard_rankings(sort_by, min(limit, 100))  # Cap at 100
        
        # Get total user count with error handling
        try:
            total_users = User.query.count()
        except Exception:
            total_users = len(rankings) if rankings else 0
            
    except Exception as e:
        # Handle database errors gracefully
        from flask import flash
        flash('Unable to load leaderboard data at this time. Please try again later.', 'error')
        rankings = []
        total_users = 0
    
    return render_template('stats/leaderboard.html', 
                         rankings=rankings, 
                         sort_by=sort_by,
                         total_users=total_users)

@stats_bp.route('/community')
def community_stats():
    """Display community-wide statistics"""
    stats = {
        'total_users': User.query.count(),
        'total_bets': db.session.query(func.sum(User.total_bets)).scalar() or 0,
        'total_wagered': db.session.query(func.sum(Bet.wager_amount)).filter(Bet.status != 'cancelled').scalar() or 0,
        'total_games': Game.query.filter_by(status='final').count(),
        'active_bets': Bet.query.filter_by(status='pending').count(),
        'biggest_bet': db.session.query(func.max(Bet.wager_amount)).filter(Bet.status != 'cancelled').scalar() or 0,
        'biggest_win': db.session.query(func.max(Bet.actual_payout)).scalar() or 0,
        'avg_bet_size': db.session.query(func.avg(Bet.wager_amount)).filter(Bet.status != 'cancelled').scalar() or 0
    }
    
    # Get top winners
    top_winners = User.query.order_by(desc(User.balance)).limit(5).all()
    
    # Get most active bettors
    most_active = User.query.order_by(desc(User.total_bets)).limit(5).all()
    
    # Get recent big wins
    recent_wins = Bet.query.filter_by(status='won')\
        .order_by(desc(Bet.actual_payout))\
        .limit(10).all()
    
    return render_template('stats/community.html', 
                         stats=stats, 
                         top_winners=top_winners,
                         most_active=most_active,
                         recent_wins=recent_wins)

@stats_bp.route('/profile/<string:discord_id>')
def user_profile(discord_id):
    """Display user profile and statistics"""
    user = User.query.filter_by(discord_id=discord_id).first_or_404()
    
    # Get user's recent bets
    recent_bets = Bet.query.filter_by(user_id=user.id).filter(Bet.status != 'cancelled')\
        .order_by(desc(Bet.placed_at))\
        .limit(10).all()
    
    # Calculate additional statistics
    stats = {
        'total_wagered': db.session.query(func.sum(Bet.wager_amount))\
            .filter(Bet.user_id == user.id, Bet.status != 'cancelled').scalar() or 0,
        'total_won': db.session.query(func.sum(Bet.actual_payout))\
            .filter(Bet.user_id == user.id, Bet.status == 'won').scalar() or 0,
        'favorite_team': get_favorite_team(user.id),
        'best_streak': calculate_best_streak(user.id),
        'current_streak': calculate_current_streak(user.id)
    }
    
    return render_template('stats/profile.html', 
                         user=user, 
                         recent_bets=recent_bets,
                         stats=stats)

def get_favorite_team(user_id):
    """Get user's most bet on team"""
    result = db.session.query(
        Bet.team_picked,
        func.count(Bet.id).label('count')
    ).filter(Bet.user_id == user_id, Bet.status != 'cancelled')\
     .group_by(Bet.team_picked)\
     .order_by(desc('count'))\
     .first()
    
    return result[0] if result else None

def calculate_best_streak(user_id):
    """Calculate user's best winning streak"""
    bets = Bet.query.filter_by(user_id=user_id)\
        .filter(Bet.status.in_(['won', 'lost']))\
        .order_by(Bet.settled_at).all()
    
    best_streak = 0
    current_streak = 0
    
    for bet in bets:
        if bet.status == 'won':
            current_streak += 1
            best_streak = max(best_streak, current_streak)
        else:
            current_streak = 0
    
    return best_streak

def calculate_current_streak(user_id):
    """Calculate user's current streak (positive for wins, negative for losses)"""
    recent_bets = Bet.query.filter_by(user_id=user_id)\
        .filter(Bet.status.in_(['won', 'lost']))\
        .order_by(desc(Bet.settled_at))\
        .limit(20).all()
    
    if not recent_bets:
        return 0
    
    streak = 0
    streak_type = recent_bets[0].status
    
    for bet in recent_bets:
        if bet.status == streak_type:
            streak += 1
        else:
            break
    
    return streak if streak_type == 'won' else -streak

@stats_bp.route('/analytics')
@login_required
def analytics():
    """Display comprehensive analytics dashboard"""
    current_user = get_current_user()
    
    # Get week-based statistics
    week_stats = get_weekly_stats()
    
    # Get user's performance over time
    user_performance = get_user_performance_data(current_user.id) if current_user else []
    
    # Get game-by-game betting distribution
    game_distributions = get_recent_game_distributions()
    
    # Get overall community insights
    community_insights = get_community_insights()
    
    return render_template('stats/analytics.html',
                         week_stats=week_stats,
                         user_performance=user_performance,
                         game_distributions=game_distributions,
                         community_insights=community_insights)

@stats_bp.route('/api/weekly-stats')
def api_weekly_stats():
    """API endpoint for weekly statistics data"""
    return jsonify(get_weekly_stats())

@stats_bp.route('/api/user-balance/<int:user_id>')
def api_user_balance_trend(user_id):
    """API endpoint for user balance trend data"""
    return jsonify(get_user_performance_data(user_id))

@stats_bp.route('/api/weekly-games')
def api_weekly_games():
    """API endpoint for weekly games data"""
    week = request.args.get('week', 'current')
    return jsonify(get_weekly_games_data(week))

def get_weekly_stats():
    """Get comprehensive weekly betting statistics"""
    try:
        # Get all games grouped by week with betting stats
        weekly_data = db.session.query(
            Game.week,
            Game.season,
            func.count(Game.id).label('total_games'),
            func.sum(Game.total_bets).label('total_bets'),
            func.sum(Game.total_wagered).label('total_wagered'),
            func.avg(Game.total_bets).label('avg_bets_per_game'),
            func.avg(Game.total_wagered).label('avg_wagered_per_game')
        ).filter(
            Game.total_bets > 0  # Only include games with bets
        ).group_by(
            Game.week, Game.season
        ).order_by(
            Game.season.desc(), Game.week.desc()
        ).limit(10).all()
        
        # Convert to list of dictionaries
        stats = []
        for row in weekly_data:
            stats.append({
                'week': row.week,
                'season': row.season,
                'total_games': row.total_games or 0,
                'total_bets': row.total_bets or 0,
                'total_wagered': float(row.total_wagered or 0),
                'avg_bets_per_game': float(row.avg_bets_per_game or 0),
                'avg_wagered_per_game': float(row.avg_wagered_per_game or 0)
            })
        
        return stats
    except Exception as e:
        return []

def get_user_performance_data(user_id):
    """Get user's betting performance over time"""
    try:
        # Get user's bets chronologically with running balance calculation
        bets = Bet.query.filter_by(user_id=user_id).order_by(Bet.placed_at).all()
        
        user = User.query.get(user_id)
        if not user:
            return []
        
        performance_data = []
        running_balance = user.starting_balance
        
        for bet in bets:
            # Skip cancelled bets in performance tracking
            if bet.status == 'cancelled':
                continue
                
            # Update running balance based on bet outcome
            if bet.status == 'won':
                running_balance += bet.actual_payout - bet.wager_amount  # Net gain
            elif bet.status == 'lost':
                running_balance -= bet.wager_amount
            elif bet.status == 'push':
                pass  # No change for pushes
            # For pending bets, we've already deducted the wager
            
            performance_data.append({
                'date': bet.placed_at.isoformat(),
                'balance': running_balance,
                'bet_amount': bet.wager_amount,
                'bet_result': bet.status,
                'game_week': bet.game.week if bet.game else None,
                'team_picked': bet.team_picked
            })
        
        return performance_data
    except Exception as e:
        return []

def get_recent_game_distributions():
    """Get betting distribution for recent games"""
    try:
        # Get recent games with good betting activity
        recent_games = Game.query.filter(
            and_(
                Game.total_bets >= 3,  # At least 3 bets
                Game.game_time > datetime.now(timezone.utc).replace(day=1)  # This month
            )
        ).order_by(desc(Game.total_bets)).limit(15).all()
        
        distributions = []
        for game in recent_games:
            home_wagered, away_wagered = game.calculate_team_wagered_amounts()
            distributions.append({
                'game_id': game.id,
                'away_team': game.away_team,
                'away_team_abbr': game.away_team_abbr,
                'home_team': game.home_team,
                'home_team_abbr': game.home_team_abbr,
                'week': game.week,
                'game_time': game.game_time.isoformat(),
                'total_bets': game.total_bets,
                'total_wagered': game.total_wagered,
                'home_bets': game.home_bets,
                'away_bets': game.away_bets,
                'home_wagered': home_wagered,
                'away_wagered': away_wagered,
                'home_percentage': game.home_bet_percentage,
                'away_percentage': game.away_bet_percentage,
                'winner': game.winner,
                'status': game.status
            })
        
        return distributions
    except Exception as e:
        return []

def get_community_insights():
    """Get community-wide betting insights"""
    try:
        insights = {
            # Overall stats
            'total_active_users': User.query.filter(User.total_bets > 0).count(),
            'total_games_bet_on': Game.query.filter(Game.total_bets > 0).count(),
            'average_bets_per_user': db.session.query(func.avg(User.total_bets)).filter(User.total_bets > 0).scalar() or 0,
            
            # Betting patterns
            'most_popular_team': get_most_popular_team(),
            'biggest_upset': get_biggest_upset(),
            
            # Financial stats
            'total_money_in_play': db.session.query(func.sum(Bet.wager_amount)).filter(Bet.status == 'pending').scalar() or 0,
            'biggest_potential_payout': db.session.query(func.max(Bet.potential_payout)).filter(Bet.status == 'pending').scalar() or 0,
            'average_bet_size_this_week': get_average_bet_size(),
            
            # Accolades
            'accolades': get_community_accolades()
        }
        
        return insights
    except Exception as e:
        return {}

def get_most_popular_team():
    """Get the team with the most bets placed on them"""
    try:
        result = db.session.query(
            Bet.team_picked,
            func.count(Bet.id).label('bet_count')
        ).filter(Bet.status != 'cancelled').group_by(Bet.team_picked).order_by(desc('bet_count')).first()
        
        return {'team': result[0], 'bet_count': result[1]} if result else None
    except:
        return None

def get_highest_scoring_week():
    """Get the week with the most betting activity"""
    try:
        result = db.session.query(
            Game.week,
            func.sum(Game.total_bets).label('total_bets')
        ).group_by(Game.week).order_by(desc('total_bets')).first()
        
        return {'week': result[0], 'total_bets': result[1]} if result else None
    except:
        return None

def get_biggest_upset():
    """Get the biggest betting upset (winning team had fewer bets)"""
    try:
        # Find completed games where the winner had fewer bets than the loser
        games = Game.query.filter(
            and_(
                Game.status == 'final',
                Game.winner != None,
                Game.total_bets >= 5  # Minimum betting activity
            )
        ).all()
        
        biggest_upset = None
        max_upset_ratio = 0
        
        for game in games:
            if game.winner == game.home_team:
                winner_bets = game.home_bets
                loser_bets = game.away_bets
            else:
                winner_bets = game.away_bets
                loser_bets = game.home_bets
                
            if winner_bets > 0 and loser_bets > winner_bets:
                upset_ratio = loser_bets / winner_bets
                if upset_ratio > max_upset_ratio:
                    max_upset_ratio = upset_ratio
                    biggest_upset = {
                        'game': f"{game.away_team} @ {game.home_team}",
                        'week': game.week,
                        'winner': game.winner,
                        'winner_bets': winner_bets,
                        'loser_bets': loser_bets,
                        'upset_ratio': upset_ratio
                    }
        
        return biggest_upset
    except:
        return None

def get_average_bet_size():
    """Get average bet size for recent betting activity"""
    try:
        # Instead of guessing current week, get average from all recent bets
        # This is more reliable and shows actual betting patterns
        avg_bet = db.session.query(func.avg(Bet.wager_amount)).filter(
            Bet.status != 'cancelled'
        ).scalar()
        
        return float(avg_bet) if avg_bet else 0.0
    except:
        return 0.0

def get_weekly_games_data(week):
    """Get games data for a specific week with betting information"""
    try:
        # Determine which week to query
        if week == 'current':
            # Get the most recent week with games
            current_week_query = db.session.query(func.max(Game.week)).filter(
                Game.game_time >= datetime.now(timezone.utc) - timedelta(days=7)
            ).scalar()
            week_num = current_week_query or 1
        else:
            week_num = int(week)
        
        # Get games for the specified week
        games = Game.query.filter_by(week=week_num).order_by(Game.game_time).all()
        
        games_data = []
        for game in games:
            # Calculate wagered amounts from actual bets
            home_wagered, away_wagered = game.calculate_team_wagered_amounts()
            
            games_data.append({
                'id': game.id,
                'away_team': game.away_team,
                'away_team_abbr': game.away_team_abbr,
                'home_team': game.home_team,
                'home_team_abbr': game.home_team_abbr,
                'week': game.week,
                'game_time': game.game_time.isoformat(),
                'status': game.status,
                'total_bets': game.total_bets,
                'total_wagered': float(game.total_wagered),
                'home_bets': game.home_bets,
                'away_bets': game.away_bets,
                'home_wagered': float(home_wagered),
                'away_wagered': float(away_wagered),
                'winner': game.winner,
                'is_tie': game.is_tie,
                'home_score': game.home_score,
                'away_score': game.away_score
            })
        
        return games_data
    except Exception as e:
        return []

def get_community_accolades():
    """Calculate fun accolades for community members"""
    try:
        accolades = {}
        
        # Money-Based Accolades
        accolades['high_roller'] = get_accolade_high_roller()
        accolades['penny_pincher'] = get_accolade_penny_pincher()
        accolades['all_in_andy'] = get_accolade_all_in_andy()
        accolades['broke_as_joke'] = get_accolade_broke_as_joke()
        accolades['money_bags'] = get_accolade_money_bags()
        accolades['minimalist'] = get_accolade_minimalist()
        accolades['feast_or_famine'] = get_accolade_feast_or_famine()
        
        # Betting Pattern Accolades
        accolades['hometown_hero'] = get_accolade_hometown_hero()
        accolades['road_warrior'] = get_accolade_road_warrior()
        accolades['contrarian'] = get_accolade_contrarian()
        accolades['one_trick_pony'] = get_accolade_one_trick_pony()
        
        # Performance Accolades
        accolades['indecisive'] = get_accolade_indecisive()
        accolades['rabbits_foot'] = get_accolade_rabbits_foot()
        accolades['cursed'] = get_accolade_cursed()
        accolades['hot_streak_hero'] = get_accolade_hot_streak_hero()
        accolades['crash_and_burn'] = get_accolade_crash_and_burn()
        accolades['jinx'] = get_accolade_jinx()
        accolades['crystal_ball'] = get_accolade_crystal_ball()
        
        # Timing Accolades
        accolades['early_bird'] = get_accolade_early_bird()
        accolades['last_call'] = get_accolade_last_call()
        accolades['prime_time_player'] = get_accolade_prime_time_player()
        
        # Situational Accolades
        accolades['upset_specialist'] = get_accolade_upset_specialist()
        accolades['blowout_predictor'] = get_accolade_blowout_predictor()
        accolades['nail_biter'] = get_accolade_nail_biter()
        
        return accolades
    except Exception as e:
        return {}

# Individual Accolade Functions

def get_accolade_high_roller():
    """Most money wagered total"""
    try:
        result = db.session.query(
            User.username,
            func.sum(Bet.wager_amount).label('total_wagered')
        ).join(Bet).filter(Bet.status != 'cancelled')\
         .group_by(User.id, User.username)\
         .order_by(desc('total_wagered')).first()
        
        return {'username': result[0], 'value': f'${result[1]:.0f}'} if result else None
    except:
        return None

def get_accolade_penny_pincher():
    """Smallest average bet size"""
    try:
        result = db.session.query(
            User.username,
            func.avg(Bet.wager_amount).label('avg_bet')
        ).join(Bet).filter(Bet.status != 'cancelled')\
         .group_by(User.id, User.username)\
         .having(func.count(Bet.id) >= 5)\
         .order_by('avg_bet').first()
        
        return {'username': result[0], 'value': f'${result[1]:.2f} avg'} if result else None
    except:
        return None

def get_accolade_all_in_andy():
    """Highest single bet placed"""
    try:
        result = db.session.query(
            User.username,
            func.max(Bet.wager_amount).label('max_bet')
        ).join(Bet).filter(Bet.status != 'cancelled')\
         .group_by(User.id, User.username)\
         .order_by(desc('max_bet')).first()
        
        return {'username': result[0], 'value': f'${result[1]:.0f}'} if result else None
    except:
        return None

def get_accolade_broke_as_joke():
    """Lowest current balance"""
    try:
        result = User.query.filter(User.total_bets > 0)\
                          .order_by(User.balance).first()
        
        return {'username': result.username, 'value': f'${result.balance:.0f}'} if result else None
    except:
        return None

def get_accolade_money_bags():
    """Highest current balance"""
    try:
        result = User.query.filter(User.total_bets > 0)\
                          .order_by(desc(User.balance)).first()
        
        return {'username': result.username, 'value': f'${result.balance:.0f}'} if result else None
    except:
        return None

def get_accolade_minimalist():
    """Most bets under $10"""
    try:
        result = db.session.query(
            User.username,
            func.count(Bet.id).label('small_bets')
        ).join(Bet).filter(and_(Bet.status != 'cancelled', Bet.wager_amount < 10))\
         .group_by(User.id, User.username)\
         .order_by(desc('small_bets')).first()
        
        return {'username': result[0], 'value': f'{result[1]} bets'} if result else None
    except:
        return None

def get_accolade_feast_or_famine():
    """Widest variance between min and max balance"""
    try:
        # This is complex - we'd need to track balance history
        # For now, use profit_loss variance as a proxy
        result = db.session.query(
            User.username,
            (User.balance - User.starting_balance).label('variance')
        ).filter(User.total_bets > 0)\
         .order_by(desc(func.abs('variance'))).first()
        
        variance = abs(result[1]) if result else 0
        return {'username': result[0], 'value': f'${variance:.0f} swing'} if result and variance > 1000 else None
    except:
        return None

def get_accolade_hometown_hero():
    """Most bets on home teams"""
    try:
        # Get users with most home team bets
        result = db.session.query(
            User.username,
            func.count(Bet.id).label('home_bets')
        ).join(Bet).join(Game)\
         .filter(and_(Bet.status != 'cancelled', Bet.team_picked == Game.home_team))\
         .group_by(User.id, User.username)\
         .order_by(desc('home_bets')).first()
        
        return {'username': result[0], 'value': f'{result[1]} home bets'} if result else None
    except:
        return None

def get_accolade_road_warrior():
    """Most bets on away teams"""
    try:
        result = db.session.query(
            User.username,
            func.count(Bet.id).label('away_bets')
        ).join(Bet).join(Game)\
         .filter(and_(Bet.status != 'cancelled', Bet.team_picked == Game.away_team))\
         .group_by(User.id, User.username)\
         .order_by(desc('away_bets')).first()
        
        return {'username': result[0], 'value': f'{result[1]} away bets'} if result else None
    except:
        return None

def get_accolade_contrarian():
    """Most bets against popular picks"""
    # This would require complex analysis - skip for now
    return None

def get_accolade_one_trick_pony():
    """Most bets on a single team"""
    try:
        result = db.session.query(
            User.username,
            Bet.team_picked,
            func.count(Bet.id).label('team_bets')
        ).join(Bet).filter(Bet.status != 'cancelled')\
         .group_by(User.id, User.username, Bet.team_picked)\
         .order_by(desc('team_bets')).first()
        
        return {'username': result[0], 'value': f'{result[2]} bets on {result[1]}'} if result and result[2] >= 5 else None
    except:
        return None

def get_accolade_indecisive():
    """Most cancelled bets"""
    try:
        result = db.session.query(
            User.username,
            func.count(Bet.id).label('cancelled_bets')
        ).join(Bet).filter(Bet.status == 'cancelled')\
         .group_by(User.id, User.username)\
         .order_by(desc('cancelled_bets')).first()
        
        return {'username': result[0], 'value': f'{result[1]} cancelled'} if result else None
    except:
        return None

def get_accolade_rabbits_foot():
    """Most won bets"""
    try:
        result = db.session.query(
            User.username,
            func.count(Bet.id).label('won_bets')
        ).join(Bet).filter(Bet.status == 'won')\
         .group_by(User.id, User.username)\
         .order_by(desc('won_bets')).first()
        
        return {'username': result[0], 'value': f'{result[1]} wins'} if result else None
    except:
        return None

def get_accolade_cursed():
    """Most lost bets"""
    try:
        result = db.session.query(
            User.username,
            func.count(Bet.id).label('lost_bets')
        ).join(Bet).filter(Bet.status == 'lost')\
         .group_by(User.id, User.username)\
         .order_by(desc('lost_bets')).first()
        
        return {'username': result[0], 'value': f'{result[1]} losses'} if result else None
    except:
        return None

def get_accolade_hot_streak_hero():
    """Longest winning streak (simplified)"""
    # Complex calculation - using total wins as proxy for now
    try:
        result = User.query.filter(User.total_bets >= 10)\
                          .order_by(desc(User.winning_bets)).first()
        
        return {'username': result.username, 'value': f'{result.winning_bets} total wins'} if result else None
    except:
        return None

def get_accolade_crash_and_burn():
    """Longest losing streak (simplified)"""
    try:
        result = User.query.filter(User.total_bets >= 10)\
                          .order_by(desc(User.losing_bets)).first()
        
        return {'username': result.username, 'value': f'{result.losing_bets} total losses'} if result else None
    except:
        return None

def get_accolade_jinx():
    """User whose teams lose most often"""
    # Complex - skip for now
    return None

def get_accolade_crystal_ball():
    """Highest win percentage with 10+ bets"""
    try:
        result = User.query.filter(User.total_bets >= 10)\
                          .order_by(desc(User.winning_bets * 100.0 / User.total_bets)).first()
        
        win_pct = (result.winning_bets / result.total_bets * 100) if result and result.total_bets > 0 else 0
        return {'username': result.username, 'value': f'{win_pct:.1f}%'} if result and win_pct > 0 else None
    except:
        return None

def get_accolade_early_bird():
    """Most bets placed early (simplified - most total bets as proxy)"""
    try:
        result = User.query.filter(User.total_bets > 0)\
                          .order_by(desc(User.total_bets)).first()
        
        return {'username': result.username, 'value': f'{result.total_bets} bets'} if result else None
    except:
        return None

def get_accolade_last_call():
    """Most bets placed close to game time"""
    # Complex timing analysis - skip for now
    return None

def get_accolade_prime_time_player():
    """Most bets on Monday/Thursday games"""
    # Would need game day analysis - skip for now
    return None

def get_accolade_upset_specialist():
    """Most wins on underdog teams"""
    # Complex underdog analysis - skip for now  
    return None

def get_accolade_blowout_predictor():
    """Most wins on blowout games"""
    # Need score differential analysis - skip for now
    return None

def get_accolade_nail_biter():
    """Most bets on close games"""
    # Need close game analysis - skip for now
    return None