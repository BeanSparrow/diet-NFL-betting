from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_discord import DiscordOAuth2Session
import os

db = SQLAlchemy()
migrate = Migrate()
discord = DiscordOAuth2Session()

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    from config import config
    app.config.from_object(config[config_name])
    
    # Validate Discord configuration
    required_discord_config = ['DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET', 'DISCORD_REDIRECT_URI']
    for config_key in required_discord_config:
        if not app.config.get(config_key):
            raise ValueError(f"Missing required Discord configuration: {config_key}")
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    discord.init_app(app)
    
    # Register blueprints
    from app.routes import main_bp, auth_bp, betting_bp, stats_bp, api_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(betting_bp, url_prefix='/betting')
    app.register_blueprint(stats_bp, url_prefix='/stats')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp)
    
    # Register development routes if in debug mode
    if app.config['DEBUG']:
        from app.routes.dev import dev_bp
        app.register_blueprint(dev_bp, url_prefix='/dev')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Initialize and configure scheduler
    if not app.config.get('TESTING', False):
        from app.services.scheduler import init_scheduler, setup_default_jobs
        scheduler = init_scheduler(app)
        setup_default_jobs(scheduler)
        
        # Start scheduler for non-testing environments
        try:
            scheduler.start()
        except Exception as e:
            app.logger.error(f"Failed to start scheduler: {e}")
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Template filters
    @app.template_filter('currency')
    def currency_filter(value):
        """Format value as currency"""
        return f"${value:,.2f}"
    
    @app.template_filter('percentage')
    def percentage_filter(value):
        """Format value as percentage"""
        return f"{value:.1f}%"
    
    # Context processor to make current_user available in all templates
    @app.context_processor
    def inject_user():
        from app.models import get_current_user
        return dict(current_user=get_current_user())
    
    return app