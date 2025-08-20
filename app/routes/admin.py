"""Admin routes for managing the Diet NFL Betting application"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from functools import wraps
from app.models import User, Game, Bet, get_current_user
from app import db
from app.routes import admin_bp
from app.services.espn_service import ESPNService
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
    # Exclude cancelled bets from total count
    total_bets = Bet.query.filter(Bet.status != 'cancelled').count()
    total_games = Game.query.count()
    
    # Recent users (last 10)
    recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
    
    # Recent bets (last 10) - exclude cancelled bets
    recent_bets = db.session.query(Bet).join(User).join(Game).filter(Bet.status != 'cancelled').order_by(desc(Bet.placed_at)).limit(10).all()
    
    # Active games
    active_games = Game.query.filter(Game.status.in_(['scheduled', 'in_progress'])).limit(5).all()
    
    # Calculate total money wagered - exclude cancelled bets
    total_wagered = db.session.query(func.sum(Bet.wager_amount)).filter(Bet.status != 'cancelled').scalar() or 0
    
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

@admin_bp.route('/admin/bets/<int:bet_id>/cancel', methods=['POST'])
@admin_required
def cancel_bet(bet_id):
    """Admin function to cancel any pending bet"""
    try:
        # Get the bet
        bet = Bet.query.get_or_404(bet_id)
        
        # Check if bet can be cancelled
        if bet.status != 'pending':
            flash(f'Cannot cancel bet: Status is {bet.status}. Only pending bets can be cancelled.', 'danger')
            return jsonify({
                'success': False,
                'message': f'Cannot cancel bet: Status is {bet.status}'
            }), 400
        
        # Admin can cancel any pending bet regardless of timing restrictions
        # Update bet status
        bet.status = 'cancelled'
        bet.settled_at = datetime.now(timezone.utc)
        
        # Refund the wager amount to the user
        bet.user.balance += bet.wager_amount
        
        # Update game statistics (reverse the bet placement)
        game = bet.game
        game.total_bets -= 1
        game.total_wagered -= bet.wager_amount
        if bet.team_picked == game.home_team:
            game.home_bets -= 1
            game.home_wagered -= bet.wager_amount
        else:
            game.away_bets -= 1
            game.away_wagered -= bet.wager_amount
        
        # Commit the transaction
        db.session.commit()
        
        flash(f'Successfully cancelled bet for {bet.user.username}. Refunded ${bet.wager_amount:.2f}.', 'success')
        return jsonify({
            'success': True,
            'message': f'Bet cancelled successfully. ${bet.wager_amount:.2f} refunded to {bet.user.username}.',
            'refund_amount': bet.wager_amount,
            'username': bet.user.username
        })
        
    except Exception as e:
        db.session.rollback()
        # Add detailed error logging
        import traceback
        full_error = traceback.format_exc()
        print(f"DETAILED CANCELLATION ERROR: {full_error}")
        
        error_msg = f'Error cancelling bet: {str(e)}'
        flash(error_msg, 'danger')
        return jsonify({
            'success': False,
            'message': error_msg,
            'detailed_error': str(e),  # Include detailed error in response
            'error_type': type(e).__name__
        }), 500

@admin_bp.route('/admin/games')
@admin_required
def games():
    """View and manage games"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    week_filter = request.args.get('week', '', type=str)
    season_filter = request.args.get('season', '', type=str)
    
    query = Game.query
    
    if status_filter:
        query = query.filter(Game.status == status_filter)
    
    if week_filter:
        query = query.filter(Game.week == int(week_filter))
    
    if season_filter:
        query = query.filter(Game.season == int(season_filter))
    
    # Order by week and game_time for better organization
    games = query.order_by(Game.week.asc(), Game.game_time.asc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get available weeks and seasons for filters
    available_weeks = db.session.query(Game.week).distinct().order_by(Game.week).all()
    available_weeks = [w[0] for w in available_weeks if w[0] is not None]
    
    available_seasons = db.session.query(Game.season).distinct().order_by(Game.season.desc()).all()
    available_seasons = [s[0] for s in available_seasons if s[0] is not None]
    
    return render_template('admin/games.html', 
                         games=games, 
                         status_filter=status_filter,
                         week_filter=week_filter,
                         season_filter=season_filter,
                         available_weeks=available_weeks,
                         available_seasons=available_seasons)

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

@admin_bp.route('/admin/fetch_season_schedule', methods=['POST'])
@admin_required
def fetch_season_schedule():
    """Manually fetch full season schedule from ESPN API"""
    try:
        # Get parameters from request
        year = request.json.get('year', datetime.now().year)
        weeks = request.json.get('weeks')  # Optional: specific weeks to fetch
        
        # Create ESPN service instance
        espn_service = ESPNService()
        
        # Fetch the full season schedule
        result = espn_service.fetch_full_season_schedule(year=year, weeks=weeks)
        
        if result['success']:
            flash(f'Successfully fetched season schedule: {result["games_processed"]} games '
                  f'({result["created"]} new, {result["updated"]} updated)', 'success')
            return jsonify({
                'success': True,
                'message': f'Fetched {result["games_processed"]} games',
                'details': result
            })
        elif result.get('partial_success'):
            flash(f'Partially fetched season schedule: {result["games_processed"]} games '
                  f'({result["weeks_fetched"]}/{result["weeks_requested"]} weeks successful)', 'warning')
            return jsonify({
                'success': False,
                'partial': True,
                'message': f'Partial fetch: {result["games_processed"]} games',
                'details': result,
                'errors': result.get('errors', [])
            })
        else:
            flash(f'Failed to fetch season schedule: {result.get("error", "Unknown error")}', 'danger')
            return jsonify({
                'success': False,
                'message': f'Failed: {result.get("error", "Unknown error")}',
                'details': result
            }), 500
            
    except Exception as e:
        error_msg = f'Error fetching season schedule: {str(e)}'
        flash(error_msg, 'danger')
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500

@admin_bp.route('/admin/fetch_current_week', methods=['POST'])
@admin_required
def fetch_current_week():
    """Manually fetch current week's games from ESPN API"""
    try:
        # Create ESPN service instance
        espn_service = ESPNService()
        
        # Fetch current week (same as scheduler does)
        result = espn_service.fetch_and_update_current_week()
        
        if result['success']:
            flash(f'Successfully fetched current week: {result["games_processed"]} games '
                  f'({result["created"]} new, {result["updated"]} updated)', 'success')
            return jsonify({
                'success': True,
                'message': f'Fetched {result["games_processed"]} games',
                'details': result
            })
        else:
            flash(f'Failed to fetch current week: {result.get("error", "Unknown error")}', 'danger')
            return jsonify({
                'success': False,
                'message': f'Failed: {result.get("error", "Unknown error")}',
                'details': result
            }), 500
            
    except Exception as e:
        error_msg = f'Error fetching current week: {str(e)}'
        flash(error_msg, 'danger')
        return jsonify({
            'success': False,
            'message': error_msg
        }), 500