# Script para forzar el borrado de la tabla billing_event y mostrar cuántos registros tenía
# Ejecuta: python tools/force_drop_billing_event.py

from app import db, create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        result = db.session.execute(text('SELECT COUNT(*) FROM billing_event'))
        count = result.scalar()
        print(f"Registros en billing_event antes de borrar: {count}")
    except Exception as e:
        print("No se pudo contar registros (probablemente la tabla no existe):", e)
    db.session.execute(text('DROP TABLE IF EXISTS billing_event CASCADE;'))
    db.session.commit()
    print('Tabla billing_event eliminada (forzado).')
