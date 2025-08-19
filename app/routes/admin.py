"""Admin routes for managing the Diet NFL Betting application"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from functools import wraps
from app.models import User, Game, Bet, get_current_user
from app import db
from app.routes import admin_bp
from datetime import datetime, timezone
from sqlalchemy import func, desc

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            flash('Please log in to access admin area.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin')
@admin_required
def dashboard():
    """Admin dashboard with overview statistics"""
    # Get basic stats
    total_users = User.query.count()
    total_bets = Bet.query.count()
    total_games = Game.query.count()
    
    # Recent users (last 10)
    recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
    
    # Recent bets (last 10)
    recent_bets = db.session.query(Bet).join(User).join(Game).order_by(desc(Bet.placed_at)).limit(10).all()
    
    # Active games
    active_games = Game.query.filter(Game.status.in_(['scheduled', 'in_progress'])).limit(5).all()
    
    # Calculate total money wagered
    total_wagered = db.session.query(func.sum(Bet.wager_amount)).scalar() or 0
    
    stats = {
        'total_users': total_users,
        'total_bets': total_bets,
        'total_games': total_games,
        'total_wagered': total_wagered,
        'recent_users': recent_users,
        'recent_bets': recent_bets,
        'active_games': active_games
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/admin/users')
@admin_required
def users():
    """View and manage users"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.discord_id.contains(search),
                User.email.contains(search) if search else False
            )
        )
    
    users = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html', users=users, search=search)

@admin_bp.route('/admin/users/<int:user_id>')
@admin_required
def user_detail(user_id):
    """View detailed user information"""
    user = User.query.get_or_404(user_id)
    
    # Get user's bets
    user_bets = Bet.query.filter_by(user_id=user.id).join(Game).order_by(desc(Bet.placed_at)).limit(20).all()
    
    # Calculate user stats
    user_stats = {
        'total_wagered': sum(bet.wager_amount for bet in user.bets),
        'net_profit': user.balance - user.starting_balance,
        'win_rate': (user.winning_bets / user.total_bets * 100) if user.total_bets > 0 else 0
    }
    
    return render_template('admin/user_detail.html', user=user, bets=user_bets, user_stats=user_stats)

@admin_bp.route('/admin/users/<int:user_id>/toggle_admin', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    user = User.query.get_or_404(user_id)
    current_user = get_current_user()
    
    # Don't allow removing your own admin status
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot modify your own admin status'}), 400
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin access {status} for {user.username}', 'success')
    
    return jsonify({'success': True, 'is_admin': user.is_admin})

@admin_bp.route('/admin/bets')
@admin_required
def bets():
    """View and manage bets"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = db.session.query(Bet).join(User).join(Game)
    
    if status_filter:
        query = query.filter(Bet.status == status_filter)
    
    bets = query.order_by(desc(Bet.placed_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/bets.html', bets=bets, status_filter=status_filter)

@admin_bp.route('/admin/games')
@admin_required
def games():
    """View and manage games"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    
    query = Game.query
    
    if status_filter:
        query = query.filter(Game.status == status_filter)
    
    games = query.order_by(desc(Game.game_time)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/games.html', games=games, status_filter=status_filter)

@admin_bp.route('/admin/games/<int:game_id>')
@admin_required
def game_detail(game_id):
    """View detailed game information"""
    game = Game.query.get_or_404(game_id)
    
    # Get all bets for this game
    game_bets = db.session.query(Bet).join(User).filter(Bet.game_id == game.id).order_by(desc(Bet.placed_at)).all()
    
    # Calculate betting statistics
    home_bets = [bet for bet in game_bets if bet.team_picked == game.home_team]
    away_bets = [bet for bet in game_bets if bet.team_picked == game.away_team]
    
    betting_stats = {
        'total_bets': len(game_bets),
        'total_wagered': sum(bet.wager_amount for bet in game_bets),
        'home_bets_count': len(home_bets),
        'away_bets_count': len(away_bets),
        'home_wagered': sum(bet.wager_amount for bet in home_bets),
        'away_wagered': sum(bet.wager_amount for bet in away_bets),
    }
    
    return render_template('admin/game_detail.html', game=game, bets=game_bets, betting_stats=betting_stats)