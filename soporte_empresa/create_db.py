from app import create_app, db

app = create_app()
# ensure instance folder exists (Flask may need this for the SQLite file)
import os
instance_path = app.instance_path
os.makedirs(instance_path, exist_ok=True)

with app.app_context():
    db.create_all()
    print('Database tables created, current URI:', app.config['SQLALCHEMY_DATABASE_URI'])
