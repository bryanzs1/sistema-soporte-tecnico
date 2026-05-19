from sqlalchemy import inspect, text
from app import create_app, db

app = create_app('config.ProductionConfig')

with app.app_context():
    inspector = inspect(db.engine)
    existing_cols = {c['name'] for c in inspector.get_columns('ticket')}

    alterations = []
    if 'sla_due_at' not in existing_cols:
        alterations.append('ALTER TABLE ticket ADD COLUMN sla_due_at TIMESTAMP')
    if 'first_response_at' not in existing_cols:
        alterations.append('ALTER TABLE ticket ADD COLUMN first_response_at TIMESTAMP')
    if 'resolved_at' not in existing_cols:
        alterations.append('ALTER TABLE ticket ADD COLUMN resolved_at TIMESTAMP')
    if 'reopened_count' not in existing_cols:
        alterations.append('ALTER TABLE ticket ADD COLUMN reopened_count INTEGER NOT NULL DEFAULT 0')

    for sql in alterations:
        db.session.execute(text(sql))

    db.create_all()
    db.session.commit()

print('OK Phase1 schema applied')
