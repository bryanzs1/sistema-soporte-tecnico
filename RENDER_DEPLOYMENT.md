# Render.com Deployment Guide

## Overview
Esta rama (`render-production`) contiene la configuración necesaria para desplegar el proyecto en Render.com sin afectar tu instalación local.

## Archivos de Configuración

- **Procfile** - Instrucciones para ejecutar la app en Render
- **render.yaml** - Blueprint de Render para recrear servicio web + PostgreSQL administrado
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
2. Click en "New +" → "Blueprint"
3. Conecta tu repositorio GitHub
4. Selecciona rama `render-production`
5. Render detectará `render.yaml` y creará:
	- el servicio web `soporte-tecnico`
	- la base PostgreSQL `soporte-tecnico-db`
6. Este blueprint está ajustado para recursos `free` de Render.

### 4. Variables de Entorno en Render
En el dashboard de Render, agrega estas variables:
```
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=(se genera automáticamente si creas el servicio desde el Blueprint)
DATABASE_URL=(Render la enlaza automáticamente a la base `soporte-tecnico-db`)
DEFAULT_ADMIN_USERNAME=(recomendado)
DEFAULT_ADMIN_PASSWORD=(recomendado)
DEFAULT_ADMIN_EMAIL=(recomendado)
```

### 5. Si Render borró tu base anterior
1. Entra al dashboard y confirma si la base antigua ya no existe.
2. Si ya no existe, vuelve a desplegar el Blueprint o crea manualmente una nueva PostgreSQL en Render.
3. Si la creas manualmente, copia su `Internal Database URL` en la variable `DATABASE_URL` del web service.
4. Lanza un deploy del servicio web.
5. Durante el deploy, `preDeployCommand` ejecutará `python migrate_to_production.py`.
6. En el primer arranque, la app también ejecuta bootstrap para crear tablas faltantes y un admin inicial si defines `DEFAULT_ADMIN_*`.

### 6. Restaurar datos antiguos
- Si no tenías backup o snapshot en Render, la base eliminada no se puede recuperar desde este repositorio.
- Si sí tenías un dump `.sql`, puedes restaurarlo con `psql` apuntando a la nueva base.
- Si no hay dump, podrás recrear la estructura automáticamente, pero no los registros históricos.

### 7. Límites importantes del plan gratis
- El servicio web se desplegará en `free`.
- La base PostgreSQL se desplegará en `free`.
- Render sólo permite una base PostgreSQL gratis activa por workspace.
- La base gratis expira 30 días después de creada si no la actualizas a un plan pago.
- Los web services gratis no soportan `persistent disk`, así que los archivos locales subidos al contenedor no son permanentes.

### 8. Deploy Automático
- Cada push a `render-production` dispara un deploy automático
- Las migraciones de BD corren automáticamente vía `preDeployCommand`

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
- ⚠️ La base de datos de Render es independiente de tu base local
- ⚠️ La retención de PostgreSQL administrado depende del plan activo de Render
- ⚠️ Si necesitas doradores probados, mantén en rama `main` primero

## Próximos Pasos
1. Generar SECRET_KEY segura: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Crear cuenta GitHub y subir este repo
3. Crear cuenta Render y conectar repo
4. Testear en render.com
