# Script para listar todas las tablas en la base de datos activa
# Ejecuta: python tools/list_tables.py

from app import db, create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    result = db.session.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """))
    print("Tablas en la base de datos:")
    for row in result:
        print("-", row[0])
