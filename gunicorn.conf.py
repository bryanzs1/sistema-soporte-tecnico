import os

# Ensure Render can detect the HTTP port even when start command is `gunicorn app:app`.
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = 1  # Socket.IO requires 1 worker with eventlet
worker_class = 'eventlet'
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
worker_connections = 1000

# Logging configuration
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stdout
loglevel = 'info'
capture_output = True
