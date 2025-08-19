"""Authentication utilities for Flask-Discord integration"""

from functools import wraps
from flask import session, redirect, url_for, request, current_app


def login_required(f):
    """Decorator to require Discord authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'discord_user_id' not in session:
            # Store the next page to redirect to after login
            session['next'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current authenticated user from session"""
    from app.models import User
    if 'discord_user_id' not in session:
        return None
    return User.query.filter_by(discord_id=session['discord_user_id']).first()


def is_authenticated():
    """Check if user is currently authenticated"""
    return 'discord_user_id' in session


def get_user_id():
    """Get current user's Discord ID from session"""
    return session.get('discord_user_id')


def get_username():
    """Get current user's username from session"""
    return session.get('discord_username')