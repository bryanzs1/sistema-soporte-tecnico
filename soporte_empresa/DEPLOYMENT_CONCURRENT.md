# Guía de Despliegue para Múltiples Usuarios Simultáneos

## Requisitos Previos de Concurrencia

El sistema ha sido optimizado para soportar múltiples usuarios simultáneos. Aquí te mostramos cómo configurar y desplegar correctamente.

## 1. Base de Datos - Cambio a PostgreSQL

**IMPORTANTE**: SQLite **NO es thread-safe** para escrituras concurrentes. Debes usar **PostgreSQL** para producción.

### Instalación de PostgreSQL

#### Windows
```bash
# Descargar e instalar desde https://www.postgresql.org/download/windows/
# O usar WSL2 con Ubuntu
```

#### Linux/WSL2
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Crear Base de Datos para Producción

```bash
# Conectar a PostgreSQL
sudo -u postgres psql

# Dentro de psql:
CREATE USER soporte_user WITH PASSWORD 'contraseña_segura';
CREATE DATABASE soporte_db OWNER soporte_user;
GRANT ALL PRIVILEGES ON DATABASE soporte_db TO soporte_user;
\q
```

### Verificar Conexión

```bash
psql -h localhost -U soporte_user -d soporte_db -c "SELECT 1"
```

## 2. Variables de Entorno para Producción

Crea un archivo `.env` en la raíz del proyecto:

```bash
# Configuración de Flask
FLASK_ENV=production
FLASK_APP=wsgi.py
SECRET_KEY=tu-clave-secreta-muy-larga-aleatorio-aqui

# Base de Datos PostgreSQL (URL completa)
DATABASE_URL=postgresql://soporte_user:contraseña_segura@localhost:5432/soporte_db

# Email (opcional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=tu-email@gmail.com
MAIL_PASSWORD=tu-app-password

# Webhook para notificaciones (opcional)
CHAT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## 3. Instalación de Dependencias para Producción

```bash
# Activar virtual environment
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate.ps1  # Windows PowerShell

# Instalar driver PostgreSQL
pip install psycopg2-binary

# Instalar servidor WSGI para producción
pip install gunicorn

# Actualizar requirements.txt
pip freeze > requirements.txt
```

## 4. Inicializar Base de Datos en Producción

```bash
# Ejecutar migraciones
flask db upgrade

# Crear usuario administrador (opcional)
flask shell
>>> from app.models import User
>>> admin = User(username='admin', email='admin@example.com', role='admin')
>>> admin.set_password('password123')
>>> from app import db
>>> db.session.add(admin)
>>> db.session.commit()
>>> exit()
```

## 5. Configuración de Gunicorn para Múltiples Trabajadores

El número de workers depende de tu servidor:
- **8GB RAM, 4 CPUs**: 4 workers
- **16GB RAM, 8 CPUs**: 8 workers
- **Máquina pequeña (1GB RAM)**: 2 workers

### Comando Básico

```bash
# 4 trabajadores, timeout de 120 segundos
gunicorn -w 4 --timeout 120 --bind 0.0.0.0:5000 wsgi:app
```

### Configuración Avanzada (crear `gunicorn_config.py`)

```python
# gunicorn_config.py
import multiprocessing

# Configuración de workers
workers = multiprocessing.cpu_count() * 2
worker_class = 'sync'  # o 'gevent' para concurrencia asíncrona
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120

# Logging
accesslog = 'logs/gunicorn_access.log'
errorlog = 'logs/gunicorn_error.log'
loglevel = 'info'

# Performance
keepalive = 5
preload_app = True  # Cargar app una sola vez

# Binding
bind = '0.0.0.0:5000'
```

Luego ejecutar con:
```bash
gunicorn --config gunicorn_config.py wsgi:app
```

## 6. Nginx como Reverse Proxy (Recomendado)

### Instalación Nginx

```bash
# Linux
sudo apt install nginx

# Mac
brew install nginx
```

### Configuración Nginx (`/etc/nginx/sites-available/soporte`)

```nginx
upstream soporte_app {
    # Balanceo de carga entre múltiples workers
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name tu-dominio.com;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://soporte_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

Activar:
```bash
sudo ln -s /etc/nginx/sites-available/soporte /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 7. Monitoreo y Logging

### Logs de Aplicación

```bash
# Crear carpeta de logs
mkdir -p logs

# Monitorear logs en tiempo real
tail -f logs/gunicorn_error.log
tail -f logs/gunicorn_access.log
```

### Verificar Salud de la Aplicación

```bash
# Ver procesos Gunicorn
ps aux | grep gunicorn

# Monitorear conexiones a BD
psql -h localhost -U soporte_user -d soporte_db -c "SELECT count(*) FROM pg_stat_activity;"
```

## 8. Connection Pool Configuration

La configuración de pool está en `config.py`:

```python
# Para producción
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,              # Conexiones activas
    'pool_recycle': 1800,         # Reciclar cada 30 min
    'pool_pre_ping': True,        # Verificar conexión antes de usar
    'max_overflow': 40,           # Máximo overflow
}
```

**Estos valores se aplican automáticamente en ProductionConfig.**

## 9. Pruebas de Concurrencia

Verificar que el sistema maneja múltiples usuarios:

```bash
# Ejecutar tests de concurrencia
pytest test_concurrent_users.py -v

# Salida esperada:
# test_concurrent_user_logins PASSED
# test_concurrent_ticket_creation PASSED
# test_concurrent_ticket_updates PASSED
# test_concurrent_database_reads PASSED
# test_concurrent_ticket_option_management PASSED
# test_session_isolation PASSED
```

## 10. Ejemplo Completo: Systemd Service (Linux)

Crear `/etc/systemd/system/soporte.service`:

```ini
[Unit]
Description=Soporte Técnico Web Application
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=/var/www/soporte_empresa
Environment="PATH=/var/www/soporte_empresa/venv/bin"
Environment="FLASK_ENV=production"
EnvironmentFile=/var/www/soporte_empresa/.env

ExecStart=/var/www/soporte_empresa/venv/bin/gunicorn \
    --config /var/www/soporte_empresa/gunicorn_config.py \
    wsgi:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable soporte
sudo systemctl start soporte
sudo systemctl status soporte
```

## 11. Checklist de Despliegue

- [ ] PostgreSQL instalado y corriendo
- [ ] Base de datos `soporte_db` creada
- [ ] Archivo `.env` configurado con DATABASE_URL
- [ ] `flask db upgrade` ejecutado
- [ ] Gunicorn instalado
- [ ] tests de concurrencia pasan: `pytest test_concurrent_users.py -v`
- [ ] Nginx configurado (si aplica)
- [ ] SSL/HTTPS habilitado (Let's Encrypt)
- [ ] Backups automáticos configurados
- [ ] Logs configurados y monitoreados

## 12. Capacidad Teórica

Con esta configuración:

| Configuración | Usuarios Simultáneos | RPM | Recomendado para |
|---|---|---|---|
| 2 workers, 4 connections | ~50-100 | 3000-5000 | Desarrollo |
| 4 workers, 20 connections | ~200-400 | 12000-20000 | Pequeña empresa |
| 8 workers, 30 connections | ~500-1000 | 30000-50000 | Empresa mediana |
| 16+ workers, 50 connections | 2000+ | 100k+ | Empresa grande |

**Nota**: Los números dependen de latencia de BD, operaciones por request, y poder del servidor.

## Troubleshooting

### "too many connections"
```sql
-- PostgreSQL
SHOW max_connections;
ALTER SYSTEM SET max_connections = 500;
-- Reiniciar: sudo systemctl restart postgresql
```

### Pool overflow errors
Aumentar `pool_size` y `max_overflow` en config.py

### Workers mueren frecuentemente
Aumentar `timeout` en Gunicorn (120+ segundos para queries lentas)

### Nginx: 502 Bad Gateway
```bash
sudo systemctl restart soporte  # Reiniciar aplicación
sudo systemctl status soporte    # Verificar estado
tail -f logs/gunicorn_error.log  # Ver errores
```

---

**Sistema listo para producción con múltiples usuarios simultáneos** ✅
