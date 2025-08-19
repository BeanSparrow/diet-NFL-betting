import os
import logging
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///diet_nfl_betting.db'
    
    # Discord OAuth
    DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
    DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')  
    DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI', 'http://localhost:5000/callback')
    DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
    DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
    DISCORD_SCOPES = ['identify', 'email']  # Required Discord OAuth scopes
    
    # Session
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    
    # Application settings
    STARTING_BALANCE = 10000  # Initial play money for new users
    MIN_BET_AMOUNT = 1
    PAYOUT_MULTIPLIER = 2.0  # Double or nothing
    
    # ESPN API settings
    ESPN_API_BASE_URL = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl'
    
    # Pagination
    BETS_PER_PAGE = 20
    USERS_PER_PAGE = 50
    
    # Timezone
    TIMEZONE = 'America/New_York'  # NFL uses Eastern Time
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Server settings
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Database connection pool settings (only for databases that support pooling)
    def __init__(self):
        super().__init__()
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///diet_nfl_betting.db')
        
        # SQLite doesn't support connection pooling
        if database_url.startswith('sqlite:'):
            self.SQLALCHEMY_ENGINE_OPTIONS = {}
        else:
            # PostgreSQL and other databases support pooling
            self.SQLALCHEMY_ENGINE_OPTIONS = {
                'pool_size': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE', 5)),
                'max_overflow': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_MAX_OVERFLOW', 10)),
                'pool_timeout': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_TIMEOUT', 30)),
                'pool_recycle': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE', 1800))
            }
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'true').lower() == 'true'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    # Development-only authentication bypass
    DEVELOPMENT_AUTH_BYPASS = True
    DEVELOPMENT_USER = {
        'discord_id': 'dev_user_123',
        'username': 'DevUser',
        'discriminator': '0001',
        'display_name': 'Development User',
        'avatar_url': 'https://cdn.discordapp.com/embed/avatars/0.png',
        'email': 'dev@example.com'
    }

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production security settings
    SESSION_COOKIE_SECURE = True  # Force HTTPS cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Use Lax for OAuth callbacks
    
    # Override host for production
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # Production logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING').upper()
    
    # Enhanced database settings for production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        # Fix for SQLAlchemy compatibility
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    # Production database pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_SIZE', 20)),
        'max_overflow': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_MAX_OVERFLOW', 40)),
        'pool_timeout': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_TIMEOUT', 60)),
        'pool_recycle': int(os.environ.get('SQLALCHEMY_ENGINE_OPTIONS_POOL_RECYCLE', 3600)),
        'pool_pre_ping': True  # Validate connections before use
    }
    
    def __init__(self):
        """Initialize production config with validation"""
        super().__init__()
        
        # Only validate if actually running in production mode
        if os.environ.get('FLASK_ENV') == 'production':
            self._validate_production_settings()
    
    def _validate_production_settings(self):
        """Validate required production settings"""
        # Validate SECRET_KEY in production (should not be default development key)
        secret_key = os.environ.get('SECRET_KEY', '')
        if not secret_key or secret_key.startswith('dev-'):
            raise ValueError("Production SECRET_KEY must be set and not use development default")
        
        # Validate Discord configuration in production  
        discord_id = os.environ.get('DISCORD_CLIENT_ID')
        discord_secret = os.environ.get('DISCORD_CLIENT_SECRET')
        if not discord_id or not discord_secret:
            raise ValueError("Discord OAuth configuration (CLIENT_ID and CLIENT_SECRET) must be set in production")
        
        # Validate database URL for production
        database_url = os.environ.get('DATABASE_URL')
        if not database_url or database_url.startswith('sqlite:'):
            raise ValueError("Production DATABASE_URL must be set and not use SQLite")
    
    # Production-specific rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'redis://localhost:6379/0')
    RATELIMIT_ENABLED = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # Test Discord configuration
    DISCORD_CLIENT_ID = 'test_client_id'
    DISCORD_CLIENT_SECRET = 'test_client_secret'
    DISCORD_REDIRECT_URI = 'http://localhost:5000/callback'
    
    # SQLite doesn't support connection pooling - override pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {}

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}