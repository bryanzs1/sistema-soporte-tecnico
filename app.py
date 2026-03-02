import os
from app import create_app

config_name = 'config.ProductionConfig' if os.environ.get('FLASK_ENV') == 'production' else 'config.DevelopmentConfig'
app = create_app(config_name)
