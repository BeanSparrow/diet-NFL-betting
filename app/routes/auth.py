from flask import render_template, redirect, url_for, flash, session, request, current_app
from app.routes import auth_bp
from app import discord, db
from app.models import User
import secrets

@auth_bp.route('/login')
def login():
    """Initiate Discord OAuth login"""
    # Check if user is already authenticated
    if 'discord_user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    # Development bypass for local testing without HTTPS
    if current_app.config.get('DEVELOPMENT_AUTH_BYPASS') and current_app.config.get('DEBUG'):
        return redirect(url_for('auth.dev_login'))
    
    # Check if Discord OAuth is configured  
    if not all([current_app.config.get('DISCORD_CLIENT_ID'), 
               current_app.config.get('DISCORD_CLIENT_SECRET')]):
        if current_app.config['DEBUG']:
            flash('Discord OAuth not configured. Use development login instead.', 'warning')
            return redirect(url_for('auth.dev_login'))
        else:
            flash('Discord OAuth is not properly configured.', 'danger')
            return redirect(url_for('main.index'))
    
    # Create Discord OAuth session and redirect to authorization
    try:
        return discord.create_session(scope=current_app.config.get('DISCORD_SCOPES', ['identify']))
    except Exception as e:
        flash(f'Error initiating Discord login: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@auth_bp.route('/callback')
def callback():
    """Handle Discord OAuth callback"""
    # Check for errors in callback
    if 'error' in request.args:
        flash(f"Discord login error: {request.args.get('error_description', 'Unknown error')}", 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Exchange authorization code for access token
        discord.callback()
        
        # Get user information from Discord
        discord_user = discord.fetch_user()
        
        # Create or update user in database
        user = User.query.filter_by(discord_id=str(discord_user.id)).first()
        
        if user is None:
            # Create new user
            user = User.create_from_discord(discord_user)
            db.session.add(user)
            db.session.commit()
            flash(f'Welcome to Diet NFL Betting, {discord_user.username}!', 'success')
        else:
            # Update existing user
            user.update_from_discord(discord_user)
            db.session.commit()
            flash(f'Welcome back, {discord_user.username}!', 'success')
        
        # Store user info in session
        session['discord_user_id'] = str(discord_user.id)
        session['discord_username'] = discord_user.username
        session.permanent = True
        
        # Redirect to next page or dashboard
        next_page = session.pop('next', None)
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f'Discord OAuth callback error: {str(e)}')
        flash(f'Error during Discord login: {str(e)}', 'danger')
        return redirect(url_for('main.index'))

@auth_bp.route('/logout')
def logout():
    """Log user out"""
    # Clear session data
    session.clear()
    
    # Revoke Discord token if exists
    try:
        if discord.authorized:
            discord.revoke()
    except Exception as e:
        current_app.logger.warning(f'Error revoking Discord token: {str(e)}')
    
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/dev-login')
def dev_login():
    """Development-only login bypass for local testing"""
    if not (current_app.config.get('DEVELOPMENT_AUTH_BYPASS') and current_app.config.get('DEBUG')):
        flash('Development login is only available in debug mode.', 'danger')
        return redirect(url_for('main.index'))
    
    # Get development user config
    dev_user_config = current_app.config.get('DEVELOPMENT_USER', {})
    
    # Create or get development user
    user = User.query.filter_by(discord_id=dev_user_config.get('discord_id')).first()
    if not user:
        user = User(
            discord_id=dev_user_config.get('discord_id'),
            username=dev_user_config.get('username'),
            discriminator=dev_user_config.get('discriminator'),
            display_name=dev_user_config.get('display_name'),
            avatar_url=dev_user_config.get('avatar_url'),
            email=dev_user_config.get('email')
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Development user created with {user.balance} starting balance!', 'success')
    else:
        flash(f'Welcome back, {user.username}!', 'success')
    
    # Set session
    session['discord_user_id'] = user.discord_id
    session.permanent = True
    
    return redirect(url_for('main.dashboard'))