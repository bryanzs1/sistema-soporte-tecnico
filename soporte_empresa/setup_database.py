"""
Script para crear base de datos PostgreSQL automaticamente
"""
import os
import sys
from sqlalchemy import create_engine, text

POSTGRES_PASSWORD = 'Diosdepactos497'
engine_url = f'postgresql://postgres:{POSTGRES_PASSWORD}@localhost:5432/postgres'

try:
    engine = create_engine(engine_url)
    
    with engine.begin() as conn:
        # Crear usuario soporte_user
        try:
            conn.execute(text('CREATE USER soporte_user WITH PASSWORD \'soporte123\''))
            print('Usuario soporte_user creado')
        except Exception as e:
            print('Usuario soporte_user ya existe')
        
        # Crear base de datos soporte_db
        try:
            conn.execute(text('CREATE DATABASE soporte_db OWNER soporte_user'))
            print('Base de datos soporte_db creada')
        except Exception as e:
            print('Base de datos soporte_db ya existe')
    
    print('PostgreSQL configurado exitosamente')
    
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)

