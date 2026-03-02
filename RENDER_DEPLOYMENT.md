# Render.com Deployment Guide

## Overview
Esta rama (`render-production`) contiene la configuración necesaria para desplegar el proyecto en Render.com sin afectar tu instalación local.

## Archivos de Configuración

- **Procfile** - Instrucciones para ejecutar la app en Render
- **render.yaml** - Configuración automática de servicios (web + PostgreSQL)
- **.env.render** - Template de variables de entorno (referencia solamente)
- **migrate_to_production.py** - Script de migración automática
- **wsgi.py** - Entry point para servidor WSGI (Gunicorn)

## Pasos para Desplegar en Render

### 1. Preparar el Repositorio
```bash
# Ya está iniciado y en rama render-production
git status  # Verifica que estés en render-production
```

### 2. Subir a GitHub
```bash
# Si aún no tienes remote configurado:
git remote add origin https://github.com/tu-usuario/sistema-soporte.git
git push -u origin render-production
```

### 3. En Render.com Dashboard
1. Crea una cuenta en https://render.com (gratis para empezar)
2. Click en "New +" → "Web Service"
3. Conecta tu repositorio GitHub
4. Selecciona rama `render-production`
5. Configuración automática desde `render.yaml`

### 4. Variables de Entorno en Render
En el dashboard de Render, agrega estas variables:
```
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=(generar una segura)
DATABASE_URL=(Render la proporciona automáticamente)
```

### 5. Deploy Automático
- Cada push a `render-production` dispara un deploy automático
- Las migraciones de BD corren automáticamente vía `release` phase

## Monitoreo
- Logs: Dashboard → Logs
- Métricas: Dashboard → Metrics
- Uptime: Dashboard → Health

## Rollback
Si algo sale mal y necesitas volver:
```bash
git checkout main      # Vuelve a rama local
git push origin main   # Tu app sigue igual
# En Render cambias manualmente a rama 'main' si quieres
```

## Notas Importantes
- ✅ Tu código local NO se modifica
- ✅ Las ramas están separadas (main para desarrollo, render-production para producción)
- ✅ SSL y dominio se configuran en Render automáticamente
- ⚠️ Base de datos en la nube (Render PostgreSQL) es diferente a tu local
- ⚠️ Si necesitas doradores probados, mantén en rama `main` primero

## Próximos Pasos
1. Generar SECRET_KEY segura: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Crear cuenta GitHub y subir este repo
3. Crear cuenta Render y conectar repo
4. Testear en render.com
