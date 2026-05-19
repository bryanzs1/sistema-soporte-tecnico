# 🔒 Guía de Seguridad - Sistema de Soporte Técnico

Este documento describe todas las medidas de seguridad implementadas en el sistema.

---

## 📊 Estado de Seguridad

| Categoría | Medida | Estado |
|-----------|--------|--------|
| **CRÍTICA** | Rate Limiting (Login) | ✅ Implementado |
| **CRÍTICA** | Headers de Seguridad (HSTS, CSP) | ✅ Implementado |
| **CRÍTICA** | SECRET_KEY Validation | ✅ Implementado |
| **ALTA** | Validación de Contraseña Fuerte | ✅ Implementado |
| **ALTA** | Auditoría Completa (AuditLog) | ✅ Implementado |
| **ALTA** | 2FA TOTP + Backup Codes | ✅ Implementado |
| **ALTA** | Account Locking | ✅ Implementado |
| **MEDIA** | CORS (Whitelist dominios) | ✅ Implementado |
| **MEDIA** | Sentry Monitoring | ✅ Implementado |
| **MEDIA** | Validación Archivos (Anti-malware) | ✅ Implementado |
| **BAJA** | Encriptación API Tokens | ✅ Implementado |
| **BAJA** | Validación API (Marshmallow) | ✅ Implementado |

---

## 🔐 Fase CRÍTICA (Implementado)

### 1. Rate Limiting en Login
**Archivo:** `app/auth.py:31`

```python
@bp.route('/login', methods=['GET', 'POST'], endpoint='login')
@limiter.limit("5 per 15 minutes")
def login():
    # ...
```

- **Protección:** 5 intentos por 15 minutos por IP
- **Respuesta:** HTTP 429 (Too Many Requests)

### 2. Headers de Seguridad
**Archivo:** `config.py:27-41`

Automáticamente agregados a todas las respuestas:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: [restricciones]
```

- **HSTS:** Fuerza HTTPS durante 1 año
- **CSP:** Solo recursos permitidos (self, fonts.googleapis, etc)
- **X-Frame-Options:** Previene clickjacking
- **X-Content-Type:** Previene MIME sniffing

### 3. Validación de SECRET_KEY
**Archivo:** `app/__init__.py:631-639`

```python
if len(secret_key) < 16:
    # Generate random 64-char key if weak
```

- Valida que SECRET_KEY tenga mínimo 16 caracteres
- Si es default o débil, genera clave aleatoria
- **Acción requerida en Render:** Setear `SECRET_KEY` env var

---

## 🔑 Fase ALTA (Implementado)

### 1. Validación de Contraseña Fuerte
**Archivo:** `app/security.py:45-85`

**Criterios NIST SP 800-63B:**
- Mínimo 8 caracteres
- No debe estar en lista de comunes
- Warnings si faltan números/mayúsculas/símbolos

```python
from app.security import PasswordValidator

is_valid, msg = PasswordValidator.validate("MyP@ssw0rd!")
```

### 2. Auditoría Completa
**Archivo:** `app/models.py:200-245` - Modelo `AuditLog`

Se registran:
- ✅ Todos los login (exitosos/fallidos)
- ✅ Cambios de contraseña
- ✅ Setup/desactivación 2FA
- ✅ Acciones de tickets
- ✅ IP Address + User Agent

```python
from app.security import AuditHelper

AuditHelper.log_login_attempt(user, success=True)
AuditHelper.log_password_change(user_id)
```

### 3. 2FA (TOTP)
**Archivo:** `app/security.py:125-179`

- Generación de secret TOTP (base32)
- QR Code para escanear en mobile
- 10 códigos de backup para recuperación
- Compatible con: Google Authenticator, Authy, Microsoft Authenticator

```python
from app.security import TOTPManager

secret = TOTPManager.generate_secret()
uri = TOTPManager.get_provisioning_uri(secret, "usuario@email.com")
qr_code = TOTPManager.get_qr_code_svg(uri)

verified = TOTPManager.verify_token(secret, "123456")  # Código del usuario
```

Endpoint: `POST /auth/verify-2fa` durante login

### 4. Account Locking
**Archivo:** `app/models.py:47-78`

```python
# En modelo User:
user.record_failed_login()  # Incrementa contador
user.is_account_locked()    # Verifica si está bloqueado
user.reset_failed_login()   # Reset en login exitoso
```

- Bloqueo automático después de 5 intentos fallidos
- Duración: 15 minutos
- Se complementa con Rate Limiting por IP

### 5. Historial de Contraseñas
**Archivo:** `app/models.py:247-276` - Modelo `PasswordHistory`

Previene reutilizar últimas 5 contraseñas:

```python
from app.models import PasswordHistory

if PasswordHistory.check_password_reuse(user_id, new_password):
    # Rechaza si fue usada recientemente
```

---

## 🌐 Fase MEDIA (Implementado)

### 1. CORS (Cross-Origin Resource Sharing)
**Archivo:** `app/__init__.py:660-668`

```python
cors_config = {
    'origins': ['https://tu-dominio.com'],
    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
    'allow_headers': ['Content-Type', 'Authorization'],
    'supports_credentials': True
}
```

**Configuración en Render:**
```env
CORS_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
```

### 2. Sentry Monitoring
**Archivo:** `app/__init__.py:669-680`

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if sentry_dsn:
    sentry_sdk.init(dsn=sentry_dsn)
```

**Configuración en Render:**
```env
SENTRY_DSN=https://tu-key@sentry.io/tu-proyecto
```

**Monitorea:**
- Excepciones y errores (500, 400, etc)
- Performance/latencia
- Errores de seguridad
- Stack traces completos
- Acceso: https://sentry.io (gratuito con límite)

### 3. Validación de Archivos (Anti-Malware)
**Archivo:** `app/security.py:200-324` - Clase `FileSecurityValidator`

**4 capas de validación:**

1. **Extensión (Whitelist)**
   - Permitidas: png, jpg, pdf, txt, doc, docx, xlsx, csv, gif, bmp, zip
   - Bloqueadas: exe, bat, sh, jar, dll, etc

2. **Magic Numbers (Firma de archivo)**
   - JPEG: `FF D8 FF`
   - PNG: `89 50 4E 47`
   - PDF: `25 50 44 46`
   - ZIP: `50 4B 03 04`

3. **Tamaño (Máximo 20MB)**
   - Rechaza vacíos o > 20MB

4. **Patrones Maliciosos**
   - Detecta: powershell, bash, curl, wget, eval(), exec(), system()
   - Elimina archivo si hay malware

```python
from app.security import FileSecurityValidator

is_valid, error, mime = FileSecurityValidator.validate(file)
is_safe, msg = FileSecurityValidator.scan_for_malware(file_path)
```

Integración automática en `app/tickets.py:_save_attachment()`

---

## 🔑 Fase BAJA (Implementado)

### 1. Encriptación de API Tokens
**Archivo:** `app/security.py:423-475` - Clase `EncryptionManager`

```python
from app.security import EncryptionManager

encrypted = EncryptionManager.encrypt("mi-token-secreto")
decrypted = EncryptionManager.decrypt(encrypted)
```

- Usa Fernet (AES-128) con SECRET_KEY
- Automático en `app/models.py:ApiToken`

### 2. Validación de API (Marshmallow)
**Archivo:** `app/api_validators.py`

Esquemas predefinidos:

```python
from app.api_validators import TicketCreateSchema, validate_request

# En endpoint:
errors = validate_request(TicketCreateSchema, request.json)
if errors:
    return {'detail': errors}, 400
```

**Esquemas disponibles:**
- `TicketCreateSchema` - Validar creación de ticket
- `TicketUpdateSchema` - Validar actualización
- `TicketCommentSchema` - Validar comentarios
- `WebhookPayloadSchema` - Validar webhooks (anti-replay)
- `APITokenCreateSchema` - Validar creación de tokens
- `PasswordChangeSchema` - Validar cambio de contraseña

---

## 🚀 Configuración en Render

**Variables de entorno requeridas:**

```env
# Obligatoria
SECRET_KEY=<clave-de-64-caracteres>

# Opcionales pero recomendadas
CORS_ORIGINS=https://tu-dominio.com
SENTRY_DSN=https://tu-key@sentry.io/proyecto
```

**Generar SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 📋 Checklist de Seguridad

- ✅ Rate Limiting en login
- ✅ Headers de seguridad (HSTS, CSP, etc)
- ✅ SECRET_KEY fuerte (mínimo 32 caracteres)
- ✅ Validación de contraseña (NIST guidelines)
- ✅ Auditoría de acciones sensibles
- ✅ 2FA habilitada para usuarios
- ✅ Account locking después de intentos fallidos
- ✅ Archivos validados (anti-malware)
- ✅ API tokens encriptados en BD
- ✅ CORS configurado correctamente
- ✅ Monitoreo de errores (Sentry)
- ✅ Validación de entrada API (Marshmallow)

---

## 🔍 Monitoreo

### Verificar logs de auditoría:

```sql
SELECT * FROM audit_log 
WHERE action = 'login' AND status = 'failure'
ORDER BY created_at DESC LIMIT 10;
```

### En Sentry:
- Ir a https://sentry.io
- Ver excepciones en tiempo real
- Configurar alertas por email

### Registros locales:
```
instance/app.log
```

---

## 🚨 Respuesta a Incidentes

### Si se sospecha compromiso:

1. **Cambiar SECRET_KEY inmediatamente** en Render
2. **Revisar auditoría** (`AuditLog`) para detectar acceso no autorizado
3. **Forzar cambio de contraseña** a todos los usuarios admin
4. **Desactivar API tokens** sospechosos
5. **Revisar Sentry** para patrones de acceso anómalo

### Bloquear usuario específico:

```python
from app.models import User
user = User.query.filter_by(username='sospechoso').first()
user.is_active = False
db.session.commit()
```

---

## 📚 Referencias

- NIST SP 800-63B (Password Guidelines)
- OWASP Top 10
- CWE/SANS Top 25

---

**Última actualización:** 2026-03-05
**Versión:** 2.0 (Fase BAJA completada)
