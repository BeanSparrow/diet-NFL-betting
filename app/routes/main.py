from flask import render_template, redirect, url_for, flash, session
from app.routes import main_bp
from app.models import User, Game, Bet, get_current_user
from app import db
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

@main_bp.route('/')
def index():
    """Home page"""
    current_user = get_current_user()
    if current_user:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """User dashboard - requires Discord authentication"""
    current_user = get_current_user()
    
    # Redirect to auth if not logged in
    if not current_user:
        flash('Please log in with Discord to access your dashboard.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Update last active time
    current_user.last_active = datetime.now(timezone.utc)
    db.session.commit()
    
    # Calculate user statistics for basic dashboard display
    stats = {
        'balance': current_user.balance,
        'starting_balance': current_user.starting_balance,
        'total_bets': current_user.total_bets,
        'winning_bets': current_user.winning_bets,
        'losing_bets': current_user.losing_bets,
        'win_percentage': current_user.win_percentage,
        'profit_loss': current_user.profit_loss
    }
    
    # Query pending bets for the user with game details
    pending_bets = db.session.query(Bet).join(Game).filter(
        Bet.user_id == current_user.id,
        Bet.status == 'pending'
    ).order_by(Game.game_time).all()
    
    return render_template('dashboard.html',
                         user=current_user,
                         stats=stats,
                         pending_bets=pending_bets)

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main_bp.route('/rules')
def rules():
    """Betting rules page"""
    return render_template('rules.html')

@main_bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('contact.html')