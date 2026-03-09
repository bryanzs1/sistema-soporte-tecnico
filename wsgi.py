"""
WSGI entry point for production deployment.
Use with Gunicorn: gunicorn -k gevent -w 1 wsgi:app
"""
from app import create_app, socketio, db
from app.models import User, Ticket, TicketOption

app = create_app()


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
