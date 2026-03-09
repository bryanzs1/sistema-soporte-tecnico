"""
WSGI entry point for production deployment with Flask-SocketIO.
For use with Gunicorn gevent workers: gunicorn -k gevent -w 1 wsgi:app
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import User, Ticket, TicketOption

# Create the Flask application instance
app = create_app()

print(f"[WSGI] Application created successfully, environment: {os.getenv('FLASK_ENV', 'production')}", flush=True)

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
    # Development server with Socket.IO
    from app import socketio
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
