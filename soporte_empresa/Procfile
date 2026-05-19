web: gunicorn -k gthread --threads 8 -w 1 --bind 0.0.0.0:$PORT wsgi:app
release: python migrate_to_production.py
