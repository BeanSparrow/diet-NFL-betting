#!/usr/bin/env python
"""Application entry point"""

import os
from app import create_app

# Get configuration from environment
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )