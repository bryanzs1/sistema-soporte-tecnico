import os

# Ensure Render can detect the HTTP port even when start command is `gunicorn app:app`.
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = 1  # Socket.IO long-polling/websocket setup is stable with a single worker here
worker_class = 'gthread'
threads = int(os.getenv('GUNICORN_THREADS', '8'))
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))

# Logging configuration
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stdout
loglevel = 'info'
capture_output = True
