# Script para eliminar la tabla billing_event de la base de datos
# Ejecuta: python tools/drop_billing_event.py

from app import db, create_app

app = create_app()

from sqlalchemy import text

with app.app_context():
    db.session.execute(text('DROP TABLE IF EXISTS billing_event CASCADE;'))
    db.session.commit()
    print('Tabla billing_event eliminada.')
