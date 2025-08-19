"""Development routes for testing without Discord OAuth"""

from flask import Blueprint, redirect, url_for, flash, current_app
from flask_login import login_user
from app.models import User

dev_bp = Blueprint('dev', __name__)

@dev_bp.route('/dev/login/<int:user_id>')
def dev_login(user_id):
    """Development login bypass - ONLY WORKS IN DEVELOPMENT MODE"""
    if not current_app.config['DEBUG']:
        flash('This feature is only available in development mode.', 'danger')
        return redirect(url_for('main.index'))
    
    user = User.query.get(user_id)
    if user:
        login_user(user, remember=True)
        flash(f'Logged in as {user.username} (DEV MODE)', 'warning')
        return redirect(url_for('main.dashboard'))
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('main.index'))

@dev_bp.route('/dev/users')
def dev_users():
    """List all test users - ONLY WORKS IN DEVELOPMENT MODE"""
    if not current_app.config['DEBUG']:
        flash('This feature is only available in development mode.', 'danger')
        return redirect(url_for('main.index'))
    
    from flask import render_template_string
    users = User.query.all()
    
    template = '''
    {% extends "base.html" %}
    {% block title %}Development Users - Diet NFL Betting{% endblock %}
    {% block content %}
    <div class="row">
        <div class="col-lg-8 mx-auto">
            <h1>Development Test Users</h1>
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Development Mode:</strong> Click any user to login without Discord OAuth.
            </div>
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Balance</th>
                        <th>Total Bets</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                    <tr>
                        <td>{{ user.id }}</td>
                        <td>
                            <img src="{{ user.avatar_url }}" width="24" height="24" class="rounded-circle me-2">
                            {{ user.username }}
                        </td>
                        <td>{{ user.balance|currency }}</td>
                        <td>{{ user.total_bets }}</td>
                        <td>
                            <a href="{{ url_for('dev.dev_login', user_id=user.id) }}" 
                               class="btn btn-sm btn-primary">
                                Login as User
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% endblock %}
    '''
    
    return render_template_string(template, users=users)