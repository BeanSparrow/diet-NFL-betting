from flask import render_template, request
from app.auth_decorators import login_required
from app.routes import stats_bp
from app.models import User, Game, Bet
from app import db
from sqlalchemy import func, desc
from typing import List, Dict, Any

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
        'total_wagered': db.session.query(func.sum(Bet.wager_amount)).scalar() or 0,
        'total_games': Game.query.filter_by(status='final').count(),
        'active_bets': Bet.query.filter_by(status='pending').count(),
        'biggest_bet': db.session.query(func.max(Bet.wager_amount)).scalar() or 0,
        'biggest_win': db.session.query(func.max(Bet.actual_payout)).scalar() or 0,
        'avg_bet_size': db.session.query(func.avg(Bet.wager_amount)).scalar() or 0
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
    recent_bets = Bet.query.filter_by(user_id=user.id)\
        .order_by(desc(Bet.placed_at))\
        .limit(10).all()
    
    # Calculate additional statistics
    stats = {
        'total_wagered': db.session.query(func.sum(Bet.wager_amount))\
            .filter_by(user_id=user.id).scalar() or 0,
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
    ).filter_by(user_id=user_id)\
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