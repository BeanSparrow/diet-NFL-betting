from flask import redirect, url_for, session, request, current_app
from flask_login import login_user, logout_user, current_user
from oauthlib.oauth2 import WebApplicationClient
import requests
import json
from datetime import datetime, timezone
from app import db
from app.models import User

# Discord OAuth endpoints
DISCORD_API_BASE_URL = 'https://discord.com/api/v10'
DISCORD_AUTHORIZATION_BASE_URL = 'https://discord.com/api/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'

class DiscordOAuth:
    """Handle Discord OAuth authentication flow"""
    
    def __init__(self, app=None):
        self.client = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.client_id = app.config.get('DISCORD_CLIENT_ID')
        self.client_secret = app.config.get('DISCORD_CLIENT_SECRET')
        self.redirect_uri = app.config.get('DISCORD_REDIRECT_URI')
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Discord OAuth credentials not configured")
        
        self.client = WebApplicationClient(self.client_id)
    
    def get_authorization_url(self):
        """Generate Discord OAuth authorization URL"""
        request_uri = self.client.prepare_request_uri(
            DISCORD_AUTHORIZATION_BASE_URL,
            redirect_uri=self.redirect_uri,
            scope=['identify', 'email'],  # Request user identity and email
            state=session.get('oauth_state', None)
        )
        return request_uri
    
    def get_token(self, authorization_response):
        """Exchange authorization code for access token"""
        code = request.args.get('code')
        
        token_url, headers, body = self.client.prepare_token_request(
            DISCORD_TOKEN_URL,
            authorization_response=authorization_response,
            redirect_url=self.redirect_uri,
            code=code
        )
        
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(self.client_id, self.client_secret)
        )
        
        if token_response.status_code != 200:
            raise Exception(f"Failed to get token: {token_response.text}")
        
        self.client.parse_request_body_response(json.dumps(token_response.json()))
        return token_response.json()
    
    def get_user_info(self, token):
        """Fetch user information from Discord"""
        uri, headers, body = self.client.add_token(f"{DISCORD_API_BASE_URL}/users/@me")
        
        userinfo_response = requests.get(
            uri,
            headers={'Authorization': f"Bearer {token['access_token']}"}
        )
        
        if userinfo_response.status_code != 200:
            raise Exception(f"Failed to get user info: {userinfo_response.text}")
        
        return userinfo_response.json()
    
    def create_or_update_user(self, user_info):
        """Create or update user in database"""
        discord_id = user_info.get('id')
        
        if not discord_id:
            raise ValueError("No Discord ID in user info")
        
        # Check if user exists
        user = User.query.filter_by(discord_id=discord_id).first()
        
        # Build avatar URL
        avatar_hash = user_info.get('avatar')
        if avatar_hash:
            avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png"
        else:
            # Default avatar based on discriminator
            default_avatar = int(user_info.get('discriminator', '0')) % 5
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"
        
        if user:
            # Update existing user
            user.username = user_info.get('username', user.username)
            user.discriminator = user_info.get('discriminator', user.discriminator)
            user.display_name = user_info.get('global_name', user.display_name)
            user.avatar_url = avatar_url
            user.email = user_info.get('email', user.email)
            user.last_login = datetime.now(timezone.utc)
            user.last_active = datetime.now(timezone.utc)
        else:
            # Create new user with starting balance
            user = User(
                discord_id=discord_id,
                username=user_info.get('username'),
                discriminator=user_info.get('discriminator'),
                display_name=user_info.get('global_name'),
                avatar_url=avatar_url,
                email=user_info.get('email'),
                balance=current_app.config.get('STARTING_BALANCE', 10000),
                starting_balance=current_app.config.get('STARTING_BALANCE', 10000),
                created_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc),
                last_active=datetime.now(timezone.utc)
            )
            db.session.add(user)
        
        db.session.commit()
        return user


def login_required_with_message(f):
    """Custom login required decorator with better messaging"""
    from functools import wraps
    from flask import flash
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in with Discord to access this page.', 'info')
            session['next'] = request.full_path
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function