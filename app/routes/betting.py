from flask import render_template, redirect, url_for, flash, request, jsonify
from app.auth_decorators import login_required
from app.routes import betting_bp
from app.models import User, Game, Bet, Transaction, get_current_user
from app.services.bet_service import BetValidator, ValidationError, validate_bet_form
from app import db
from datetime import datetime, timezone
from sqlalchemy import and_

@betting_bp.route('/games')
@login_required
def games():
    """Display available games for betting with graceful degradation"""
    week = request.args.get('week', type=int)
    games = []
    user_bets = {}
    current_user = get_current_user()
    
    try:
        # Query for games with error handling
        query = Game.query.filter(Game.status == 'scheduled')
        
        if week:
            query = query.filter_by(week=week)
        else:
            # Show current week by default
            query = query.filter(Game.game_time > datetime.now(timezone.utc))
        
        games = query.order_by(Game.game_time).all()
        
        # Get user's bets for these games
        if games and current_user:
            try:
                game_ids = [g.id for g in games]
                bets = Bet.query.filter(
                    and_(
                        Bet.user_id == current_user.id,
                        Bet.game_id.in_(game_ids),
                        Bet.status == 'pending'  # Only show pending bets
                    )
                ).all()
                user_bets = {bet.game_id: bet for bet in bets}
            except Exception as e:
                # Log error but continue without user bets
                flash('Unable to load your current bets. New bets can still be placed.', 'warning')
                user_bets = {}
                
    except Exception as e:
        # Handle database or query errors gracefully
        flash('Unable to load games at this time. Please try again later.', 'error')
        games = []
    
    return render_template('betting/games.html', 
                         games=games, 
                         user_bets=user_bets,
                         current_week=week)

@betting_bp.route('/place/<int:game_id>', methods=['GET', 'POST'])
@login_required
def place_bet(game_id):
    """Place a bet on a game"""
    game = Game.query.get_or_404(game_id)
    
    # Check if game is bettable
    if not game.is_bettable:
        flash('This game is no longer available for betting.', 'warning')
        return redirect(url_for('betting.games'))
    
    # Check if user already has a pending bet on this game
    current_user = get_current_user()
    existing_bet = Bet.query.filter_by(
        user_id=current_user.id,
        game_id=game_id,
        status='pending'  # Only check for pending bets
    ).first()
    
    if existing_bet:
        flash('You already have a bet on this game.', 'info')
        return redirect(url_for('betting.view_bet', bet_id=existing_bet.id))
    
    if request.method == 'POST':
        # Get form data
        form_data = {
            'game_id': game_id,
            'team_picked': request.form.get('team_picked'),
            'wager_amount': request.form.get('wager_amount')
        }
        
        # Validate form data
        is_valid, errors = validate_bet_form(form_data, current_user)
        
        if not is_valid:
            # Flash all validation errors
            for error in errors:
                flash(error, 'error')
        else:
            # Create bet using validator
            validator = BetValidator()
            bet = validator.create_bet(
                current_user,
                game_id,
                form_data['team_picked'],
                float(form_data['wager_amount'])
            )
            
            if bet:
                flash(f'Bet placed successfully! ${bet.wager_amount:.2f} on {bet.team_picked}', 'success')
                return redirect(url_for('betting.view_bet', bet_id=bet.id))
            else:
                # Flash validator errors
                validator.flash_errors()
    
    # The home_wagered and away_wagered fields are now maintained automatically
    
    return render_template('betting/place_bet.html', game=game)

@betting_bp.route('/place', methods=['POST'])
@login_required  
def place():
    """General bet placement endpoint for form submissions"""
    current_user = get_current_user()
    
    # Get form data
    form_data = {
        'game_id': request.form.get('game_id'),
        'team_picked': request.form.get('team_picked'),
        'wager_amount': request.form.get('wager_amount')
    }
    
    # Validate form data
    is_valid, errors = validate_bet_form(form_data, current_user)
    
    if not is_valid:
        # Flash all validation errors
        for error in errors:
            flash(error, 'error')
        # Redirect back to games page
        return redirect(url_for('betting.games'))
    
    # Create bet using validator
    validator = BetValidator()
    bet = validator.create_bet(
        current_user,
        int(form_data['game_id']),
        form_data['team_picked'],
        form_data['wager_amount']
    )
    
    if bet:
        flash(f'Bet placed successfully! ${bet.wager_amount:.2f} on {bet.team_picked}', 'success')
        return redirect(url_for('betting.view_bet', bet_id=bet.id))
    else:
        # Flash validator errors
        validator.flash_errors()
        return redirect(url_for('betting.games'))

@betting_bp.route('/bet/<int:bet_id>')
@login_required
def view_bet(bet_id):
    """View a specific bet"""
    bet = Bet.query.get_or_404(bet_id)
    current_user = get_current_user()
    
    # Ensure user owns this bet
    if bet.user_id != current_user.id:
        flash('You do not have permission to view this bet.', 'danger')
        return redirect(url_for('main.dashboard'))
    
    return render_template('betting/view_bet.html', bet=bet)

@betting_bp.route('/history')
@login_required
def betting_history():
    """View user's betting history"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    current_user = get_current_user()
    
    query = Bet.query.filter_by(user_id=current_user.id)
    
    if status_filter == 'all':
        # Exclude cancelled bets from "all" view by default
        query = query.filter(Bet.status != 'cancelled')
    else:
        query = query.filter_by(status=status_filter)
    
    bets = query.order_by(Bet.placed_at.desc()).paginate(
        page=page, 
        per_page=20,
        error_out=False
    )
    
    return render_template('betting/history.html', 
                         bets=bets, 
                         status_filter=status_filter)

@betting_bp.route('/cancel/<int:bet_id>', methods=['POST'])
@login_required
def cancel_bet(bet_id):
    """Cancel a pending bet"""
    current_user = get_current_user()
    validator = BetValidator()
    
    # Attempt to cancel the bet
    success = validator.cancel_bet(current_user, bet_id)
    
    if success:
        flash('Bet cancelled successfully. Your balance has been refunded.', 'success')
    else:
        # Flash validator errors
        for error in validator.get_errors():
            flash(error, 'error')
    
    return redirect(url_for('main.dashboard'))