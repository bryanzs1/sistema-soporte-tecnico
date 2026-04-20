# Soporte Empresa

## Preparación del entorno

1. Crear un virtualenv y activar:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configurar variables de entorno (ejemplo `.env` o en el sistema):
   ```bash
   export FLASK_APP=run.py
   export FLASK_ENV=development
   # for development we default to SQLite; set DATABASE_URL for PostgreSQL
   export DATABASE_URL=postgresql://user:pass@localhost/soporte_db
   # by default the SQLite database will be created at instance/soporte.db
   export SECRET_KEY="algo-secreto"
   # mail settings (for development you can use console backend)
   export MAIL_SERVER=localhost
   export MAIL_PORT=25
   export MAIL_DEFAULT_SENDER="noreply@example.com"
   export PAYPAL_CLIENT_ID="tu-client-id"
   export PAYPAL_CLIENT_SECRET="tu-client-secret"
   export PAYPAL_MODE="sandbox"
   export PAYPAL_DEFAULT_PLAN_ID="P-..."
   export PAYPAL_MONTHLY_PLAN_ID="P-..."
   export PAYPAL_ANNUAL_PLAN_ID="P-..."
   export PAYPAL_WEBHOOK_ID="tu-webhook-id"
   ```

### Suscripciones con PayPal

La integración actual usa PayPal Subscriptions. El flujo recomendado es entrar a `/pricing`, elegir mensual o anual y completar la aprobación en PayPal.

Configura en PayPal dos planes activos, uno mensual y otro anual, y copia sus `Plan ID` en Render usando `PAYPAL_MONTHLY_PLAN_ID` y `PAYPAL_ANNUAL_PLAN_ID`.



### Chat/Webhook notifications

The application can send updates not only by email but also via a generic chat webhook
(Slack, Teams, etc.). To enable, set the configuration variable
`CHAT_WEBHOOK_URL` to the desired incoming-webhook URL. The body of the message
is the same as the email content, so you can customise it in your chat tool.

## Migraciones

Usar Flask-Migrate para inicializar y crear la base de datos:

```bash
flask db init          # sólo la primera vez
flask db migrate -m "Initial tables"
flask db upgrade
```

> **Después de añadir el campo `creator_name`** (o cualquier otra modificación de modelo) ejecuta de nuevo:
>
> ```bash
> flask db migrate -m "Add creator_name to tickets"
> flask db upgrade
> ```
> 
> Se incluye un ejemplo de migración en `migrations/versions/0001_add_creator_name.py`.

> Para habilitar catálogo administrable de categorías/prioridades, aplica también:
>
> ```bash
> flask db migrate -m "Add ticket options catalog"
> flask db upgrade
> ```

## Roles y permisos

- Usuarios normales sólo ven sus propios tickets.
- Técnicos y administradores ven todos los tickets.
- El campo `role` en el modelo `User` define el permiso.

### Ticket metadata

### Control panel for staff

Administrators and technicians have access to a dashboard at
`/admin/dashboard`. The panel shows high-level statistics about tickets
(weekly counts, status breakdown, category breakdown) and provides
quick links to the ticket list and, for admins, user management. A
"Dashboard" link appears in the navbar when a technician or admin is
logged in.


When creating a ticket the user is now **required** to provide the name of the person reporting the issue. This value is stored in the `creator_name` column and is shown in both the ticket list and detail pages. After pulling the latest code you will need to run a database migration to add the new field (see Migraciones below).

### Filtrado de tickets

La vista de tickets (`/tickets/`) admite parámetros GET opcionales:

* `status`, `category`, `priority` – valores exactos como en el formulario.
* `start_date`, `end_date` – fechas ISO (yyyy-mm-dd) para limitar por creación.
* `keyword` – busca texto parcial en el título o la descripción.

Los mismos filtros se aplican al exportar CSV.
### Panel de administración

Los administradores pueden acceder a `/admin/users` para ver la lista de
usuarios y cambiar su rol (usuario/técnico/administrador). El enlace aparece
en la barra de navegación cuando el admin ha iniciado sesión.

Además, los administradores pueden gestionar categorías y prioridades de tickets
en `/admin/ticket-options`. Los valores agregados allí aparecen automáticamente
en el formulario de creación de tickets y en los filtros del listado.

## Ejecución

```bash
flask run
```

Acceder a `http://localhost:5000`. El enlace de registro se ha eliminado: los usuarios sólo pueden ser creados por un
administrador en el panel de administración y el correo electrónico **debe** pertenecer
a uno de los dominios corporativos autorizados: `@eie-puj.com`, `@eie-lrm.com` o `@bppclub.com`.

---

Posteriormente se pueden crear usuarios (por ejemplo una cuenta `admin`) directamente con la shell:

```python
>>> from app import db
>>> from app.models import User
>>> u = User(username='admin', email='admin@empresa.com', role='admin')
>>> u.set_password('secret')
>>> db.session.add(u)
>>> db.session.commit()
```
