"""
WSGI entry point for production deployment.
Use with Gunicorn: gunicorn -w 4 --timeout 120 wsgi:app
"""
from app import app, db
from app.models import User, Ticket, TicketOption


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
