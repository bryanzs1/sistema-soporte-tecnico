"""
WSGI entry point for production deployment.
Use with Gunicorn: gunicorn -w 4 --timeout 120 wsgi:app
"""
import os
from app import create_app, db
from app.models import User, Ticket, TicketOption

# Use ProductionConfig if FLASK_ENV=production, otherwise DevelopmentConfig
config_name = 'config.ProductionConfig' if os.environ.get('FLASK_ENV') == 'production' else 'config.DevelopmentConfig'
app = create_app(config_name)


# CLI command for production setup
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Ticket': Ticket,
        'TicketOption': TicketOption,
    }


if __name__ == '__main__':
    # Only run development server if not using Gunicorn
    app.run()
