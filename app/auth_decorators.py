"""
Custom authentication decorators for session-based authentication
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request
from app.models import get_current_user

def login_required(f):
    """
    Decorator to require authentication for routes
    Replaces flask_login.login_required with session-based auth
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated via session
        if 'discord_user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Verify user exists in database
        current_user = get_current_user()
        if not current_user:
            # Session exists but user doesn't - clear invalid session
            session.clear()
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def admin_required(f):
    """
    Decorator to require admin authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check if user is logged in
        if 'discord_user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        current_user = get_current_user()
        if not current_user:
            session.clear()
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if user is admin (you can add admin field to User model later)
        if not getattr(current_user, 'is_admin', False):
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    
    return decorated_function