from flask import Blueprint

# Create blueprints
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)
betting_bp = Blueprint('betting', __name__)
stats_bp = Blueprint('stats', __name__)
api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__)

# Import routes to register them with blueprints
from app.routes import main, auth, betting, stats, api, admin