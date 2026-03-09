import os

# Ensure Render can detect the HTTP port even when start command is `gunicorn app:app`.
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = int(os.getenv('WEB_CONCURRENCY', '2'))
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
