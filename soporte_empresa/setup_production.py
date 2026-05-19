"""
Script completo para configuración de producción
"""
import os
import sys

# Configurar variables de entorno
os.environ['FLASK_ENV'] = 'production'
os.environ['DATABASE_URL'] = 'postgresql://soporte_user:soporte123@localhost:5432/soporte_db'
os.environ['SECRET_KEY'] = 'soporte-secret-2026'

print("=" * 60)
print("CONFIGURACION DEL SISTEMA")
print("=" * 60)

# 1. Verificar conexión
print("\n1. Verificando conexión a PostgreSQL...")
try:
    from sqlalchemy import create_engine, text
    engine = create_engine('postgresql://soporte_user:soporte123@localhost:5432/soporte_db')
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Conexion OK")
except Exception as e:
    print(f"Error: {str(e)[:100]}")
    sys.exit(1)

# 2. Crear usuarios de prueba
print("\n2. Creando estructura...")
try:
    from app import create_app, db
    from app.models import User
    
    app = create_app('config.ProductionConfig')
    
    with app.app_context():
        db.create_all()
        
        # Crear admin
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@test.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Crear usuarios
        for i in range(5):
            if not User.query.filter_by(username=f'user{i}').first():
                user = User(username=f'user{i}', email=f'user{i}@test.com', role='user')
                user.set_password('password')
                db.session.add(user)
        
        db.session.commit()
        
        user_count = User.query.count()
        print(f"Usuarios creados: {user_count}")
        
except Exception as e:
    print(f"Error: {str(e)[:100]}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("LISTO PARA MULTIPLES USUARIOS")
print("=" * 60)

