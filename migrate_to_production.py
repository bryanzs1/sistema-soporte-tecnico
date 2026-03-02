"""
Migration script for Render.com production deployment
Runs automatically after code push using Procfile 'release' command
"""

import os
import sys
from app import create_app, db
from flask_migrate import upgrade

def migrate_database():
    """Apply all pending database migrations"""
    app = create_app()
    
    with app.app_context():
        print("Starting database migration...")
        try:
            upgrade()
            print("✓ Database migration completed successfully")
        except Exception as e:
            print(f"✗ Migration failed: {str(e)}", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    migrate_database()
