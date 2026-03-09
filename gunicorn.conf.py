import os

# Ensure Render can detect the HTTP port even when start command is `gunicorn app:app`.
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = 1  # Socket.IO requires 1 worker with gevent
worker_class = 'gevent'
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
worker_connections = 1000
