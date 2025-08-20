from flask import jsonify, request
from app.auth_decorators import login_required
from app.routes import api_bp
from app.models import User, Game, Bet, get_current_user
from app import db
from datetime import datetime, timezone

@api_bp.route('/user/balance')
@login_required
def get_user_balance():
    """Get current user's balance"""
    current_user = get_current_user()
    return jsonify({
        'balance': current_user.balance,
        'starting_balance': current_user.starting_balance,
        'profit_loss': current_user.profit_loss
    })

@api_bp.route('/games/upcoming')
def get_upcoming_games():
    """Get upcoming games"""
    week = request.args.get('week', type=int)
    limit = request.args.get('limit', 20, type=int)
    
    query = Game.query.filter(
        Game.status == 'scheduled',
        Game.game_time > datetime.now(timezone.utc)
    )
    
    if week:
        query = query.filter_by(week=week)
    
    games = query.order_by(Game.game_time).limit(limit).all()
    
    return jsonify([{
        'id': g.id,
        'week': g.week,
        'home_team': g.home_team,
        'away_team': g.away_team,
        'game_time': g.game_time.isoformat(),
        'total_bets': g.total_bets,
        'total_wagered': g.total_wagered,
        'home_bet_percentage': g.home_bet_percentage,
        'away_bet_percentage': g.away_bet_percentage
    } for g in games])

@api_bp.route('/games/<int:game_id>')
def get_game_details(game_id):
    """Get detailed information about a specific game"""
    game = Game.query.get_or_404(game_id)
    
    return jsonify({
        'id': game.id,
        'espn_game_id': game.espn_game_id,
        'week': game.week,
        'season': game.season,
        'home_team': game.home_team,
        'home_team_abbr': game.home_team_abbr,
        'away_team': game.away_team,
        'away_team_abbr': game.away_team_abbr,
        'game_time': game.game_time.isoformat(),
        'status': game.status,
        'home_score': game.home_score,
        'away_score': game.away_score,
        'winner': game.winner,
        'is_tie': game.is_tie,
        'total_bets': game.total_bets,
        'total_wagered': game.total_wagered,
        'home_bets': game.home_bets,
        'away_bets': game.away_bets,
        'home_bet_percentage': game.home_bet_percentage,
        'away_bet_percentage': game.away_bet_percentage,
        'is_bettable': game.is_bettable
    })

@api_bp.route('/leaderboard')
def get_leaderboard():
    """Get leaderboard data"""
    limit = request.args.get('limit', 10, type=int)
    sort_by = request.args.get('sort', 'balance')
    
    query = User.query
    
    if sort_by == 'balance':
        users = query.order_by(User.balance.desc()).limit(limit).all()
    elif sort_by == 'profit':
        users = sorted(query.all(), key=lambda u: u.profit_loss, reverse=True)[:limit]
    elif sort_by == 'wins':
        users = query.order_by(User.winning_bets.desc()).limit(limit).all()
    elif sort_by == 'win_rate':
        users = sorted(
            [u for u in query.all() if u.total_bets > 0],
            key=lambda u: u.win_percentage,
            reverse=True
        )[:limit]
    else:
        users = query.order_by(User.balance.desc()).limit(limit).all()
    
    return jsonify([{
        'rank': i + 1,
        'username': u.username,
        'discord_id': u.discord_id,
        'balance': u.balance,
        'profit_loss': u.profit_loss,
        'total_bets': u.total_bets,
        'winning_bets': u.winning_bets,
        'win_percentage': u.win_percentage
    } for i, u in enumerate(users)])

@api_bp.route('/stats/community')
def get_community_stats():
    """Get community-wide statistics"""
    from sqlalchemy import func
    
    stats = {
        'total_users': User.query.count(),
        'total_bets': db.session.query(func.sum(User.total_bets)).scalar() or 0,
        'total_wagered': db.session.query(func.sum(Bet.wager_amount)).filter(Bet.status != 'cancelled').scalar() or 0,
        'total_games': Game.query.filter_by(status='final').count(),
        'active_bets': Bet.query.filter_by(status='pending').count(),
        'average_balance': db.session.query(func.avg(User.balance)).scalar() or 0,
        'total_profit': db.session.query(
            func.sum(User.balance - User.starting_balance)
        ).scalar() or 0
    }
    
    return jsonify(stats)

@api_bp.route('/user/bets')
@login_required
def get_user_bets():
    """Get current user's bets"""
    status = request.args.get('status', 'all')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    current_user = get_current_user()
    
    query = Bet.query.filter_by(user_id=current_user.id)
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    total = query.count()
    bets = query.order_by(Bet.placed_at.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return jsonify({
        'total': total,
        'bets': [{
            'id': b.id,
            'game_id': b.game_id,
            'team_picked': b.team_picked,
            'wager_amount': b.wager_amount,
            'potential_payout': b.potential_payout,
            'actual_payout': b.actual_payout,
            'status': b.status,
            'placed_at': b.placed_at.isoformat(),
            'settled_at': b.settled_at.isoformat() if b.settled_at else None,
            'game': {
                'home_team': b.game.home_team,
                'away_team': b.game.away_team,
                'game_time': b.game.game_time.isoformat(),
                'status': b.game.status,
                'home_score': b.game.home_score,
                'away_score': b.game.away_score
            }
        } for b in bets]
    })

@api_bp.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })