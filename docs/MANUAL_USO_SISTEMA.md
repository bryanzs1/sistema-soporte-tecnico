# Manual de Uso y Referencia Detallada de Funciones

## 1. Alcance
Este manual incluye uso funcional por rol y catalogo tecnico funcion por funcion del backend principal.

## 2. Roles del sistema
- Usuario: crea, consulta, comenta, califica y reabre tickets dentro de la ventana permitida.
- Tecnico: gestiona flujo operativo de tickets, chat y conocimientos.
- Administrador: gestiona configuracion, seguridad, usuarios, integraciones, auditoria y reportes.

## 3. Modulos principales
- app/auth.py: autenticacion, password, 2FA y cierre de sesion.
- app/tickets.py: operaciones completas de tickets, chat y reaperturas.
- app/admin.py: panel administrativo, settings, KB, integraciones y auditoria.
- app/api.py: endpoints externos y webhooks.
- app/routes.py: paginas publicas, health y utilidades de sesion.
- app/models.py: entidades y reglas de negocio de datos.

## 4. Referencia detallada de funciones
La siguiente seccion describe cada funcion detectada en el paquete app.

### Modulo: app/__init__.py

#### Funcion: utcnow
- Ubicacion: app/__init__.py:44
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: _rate_limit_key
- Ubicacion: app/__init__.py:49
- Tipo: Internal helper
- Parametros: sin parametros declarados
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: translate
- Ubicacion: app/__init__.py:894
- Tipo: Application helper
- Parametros: text, lang
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: send_email
- Ubicacion: app/__init__.py:898
- Tipo: Application helper
- Parametros: subject, recipients, body, html
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Triggers email notification flow.
  - Triggers webhook notification flow.

#### Funcion: send_webhook
- Ubicacion: app/__init__.py:913
- Tipo: Application helper
- Parametros: message
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Triggers webhook notification flow.

#### Funcion: _validate_secret_key
- Ubicacion: app/__init__.py:926
- Tipo: Internal helper
- Parametros: app
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: create_app
- Ubicacion: app/__init__.py:953
- Tipo: Application helper
- Parametros: config_class
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Rolls back transaction on error.
  - Renders HTML template response.
  - Redirects browser to another route.

#### Funcion: load_user
- Ubicacion: app/__init__.py:1046
- Tipo: Application helper
- Parametros: user_id
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: inject_current_year
- Ubicacion: app/__init__.py:1072
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: _translate
- Ubicacion: app/__init__.py:1075
- Tipo: Internal helper
- Parametros: text
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: from_json_filter
- Ubicacion: app/__init__.py:1086
- Tipo: Application helper
- Parametros: value
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: update_user_activity_and_enforce_password
- Ubicacion: app/__init__.py:1097
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Persists database changes.
  - Rolls back transaction on error.
  - Redirects browser to another route.

#### Funcion: handle_unexpected_error
- Ubicacion: app/__init__.py:1156
- Tipo: Application helper
- Parametros: error
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Renders HTML template response.

### Modulo: app/admin.py

#### Funcion: utcnow
- Ubicacion: app/admin.py:18
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: _t
- Ubicacion: app/admin.py:23
- Tipo: Internal helper
- Parametros: text
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: admin_required
- Ubicacion: app/admin.py:27
- Tipo: Application helper
- Parametros: func
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: wrapper
- Ubicacion: app/admin.py:32
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: tech_or_admin_required
- Ubicacion: app/admin.py:41
- Tipo: Application helper
- Parametros: func
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: wrapper
- Ubicacion: app/admin.py:46
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: list_users
- Ubicacion: app/admin.py:58
- Tipo: HTTP endpoint
- Ruta: /users
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /users with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Rolls back transaction on error.
  - Renders HTML template response.
  - Sends user-visible feedback message.

#### Funcion: create_user
- Ubicacion: app/admin.py:73
- Tipo: HTTP endpoint
- Ruta: /users/create
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /users/create with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Rolls back transaction on error.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: edit_user
- Ubicacion: app/admin.py:102
- Tipo: HTTP endpoint
- Ruta: /users/<int:user_id>/edit
- Metodos HTTP: GET, POST
- Parametros: user_id
- Que hace: Exposes route /users/<int:user_id>/edit with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: reset_user_password
- Ubicacion: app/admin.py:118
- Tipo: HTTP endpoint
- Ruta: /users/<int:user_id>/reset-password
- Metodos HTTP: GET, POST
- Parametros: user_id
- Que hace: Exposes route /users/<int:user_id>/reset-password with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Rolls back transaction on error.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: dashboard
- Ubicacion: app/admin.py:173
- Tipo: HTTP endpoint
- Ruta: /dashboard
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /dashboard with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires technician or administrator role.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: chat_monitoring
- Ubicacion: app/admin.py:258
- Tipo: HTTP endpoint
- Ruta: /chat-monitoring
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /chat-monitoring with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: _get_chat_participants
- Ubicacion: app/admin.py:299
- Tipo: Internal helper
- Parametros: ticket
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: online_users_list
- Ubicacion: app/admin.py:334
- Tipo: HTTP endpoint
- Ruta: /online-users
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /online-users with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: online_users_data
- Ubicacion: app/admin.py:361
- Tipo: HTTP endpoint
- Ruta: /online-users/data
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /online-users/data with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.

#### Funcion: debug_online_users_json
- Ubicacion: app/admin.py:390
- Tipo: HTTP endpoint
- Ruta: /debug/online-users
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /debug/online-users with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.

#### Funcion: ticket_options
- Ubicacion: app/admin.py:416
- Tipo: HTTP endpoint
- Ruta: /ticket-options
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /ticket-options with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: delete_ticket_option
- Ubicacion: app/admin.py:441
- Tipo: HTTP endpoint
- Ruta: /ticket-options/<int:option_id>/delete
- Metodos HTTP: POST
- Parametros: option_id
- Que hace: Exposes route /ticket-options/<int:option_id>/delete with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: edit_ticket_option
- Ubicacion: app/admin.py:452
- Tipo: HTTP endpoint
- Ruta: /ticket-options/<int:option_id>/edit
- Metodos HTTP: POST
- Parametros: option_id
- Que hace: Exposes route /ticket-options/<int:option_id>/edit with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: ml_system
- Ubicacion: app/admin.py:478
- Tipo: HTTP endpoint
- Ruta: /ml-system
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /ml-system with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: ml_train
- Ubicacion: app/admin.py:535
- Tipo: HTTP endpoint
- Ruta: /ml-system/train
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /ml-system/train with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: integrations
- Ubicacion: app/admin.py:552
- Tipo: HTTP endpoint
- Ruta: /integrations
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /integrations with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Redirects browser to another route.

#### Funcion: create_api_token
- Ubicacion: app/admin.py:560
- Tipo: HTTP endpoint
- Ruta: /integrations/tokens/create
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /integrations/tokens/create with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: revoke_api_token
- Ubicacion: app/admin.py:591
- Tipo: HTTP endpoint
- Ruta: /integrations/tokens/<int:token_id>/revoke
- Metodos HTTP: POST
- Parametros: token_id
- Que hace: Exposes route /integrations/tokens/<int:token_id>/revoke with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: create_integration
- Ubicacion: app/admin.py:604
- Tipo: HTTP endpoint
- Ruta: /integrations/create
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /integrations/create with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: toggle_integration
- Ubicacion: app/admin.py:641
- Tipo: HTTP endpoint
- Ruta: /integrations/<int:integration_id>/toggle
- Metodos HTTP: POST
- Parametros: integration_id
- Que hace: Exposes route /integrations/<int:integration_id>/toggle with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: delete_integration
- Ubicacion: app/admin.py:655
- Tipo: HTTP endpoint
- Ruta: /integrations/<int:integration_id>/delete
- Metodos HTTP: POST
- Parametros: integration_id
- Que hace: Exposes route /integrations/<int:integration_id>/delete with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: ai_system
- Ubicacion: app/admin.py:668
- Tipo: HTTP endpoint
- Ruta: /ai-system
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /ai-system with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: ai_system_settings
- Ubicacion: app/admin.py:692
- Tipo: HTTP endpoint
- Ruta: /ai-system/settings
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /ai-system/settings with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: settings
- Ubicacion: app/admin.py:714
- Tipo: HTTP endpoint
- Ruta: /settings
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: settings_users
- Ubicacion: app/admin.py:722
- Tipo: HTTP endpoint
- Ruta: /settings/users
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/users with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Rolls back transaction on error.
  - Renders HTML template response.
  - Sends user-visible feedback message.

#### Funcion: settings_ticket_options
- Ubicacion: app/admin.py:743
- Tipo: HTTP endpoint
- Ruta: /settings/ticket-options
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/ticket-options with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Rolls back transaction on error.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: settings_ml
- Ubicacion: app/admin.py:782
- Tipo: HTTP endpoint
- Ruta: /settings/ml
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/ml with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: settings_ai
- Ubicacion: app/admin.py:829
- Tipo: HTTP endpoint
- Ruta: /settings/ai
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/ai with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: settings_ai_update
- Ubicacion: app/admin.py:853
- Tipo: HTTP endpoint
- Ruta: /settings/ai/settings
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/ai/settings with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: settings_integrations
- Ubicacion: app/admin.py:869
- Tipo: HTTP endpoint
- Ruta: /settings/integrations
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/integrations with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: settings_audit
- Ubicacion: app/admin.py:897
- Tipo: HTTP endpoint
- Ruta: /settings/audit
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/audit with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: settings_audit_export
- Ubicacion: app/admin.py:918
- Tipo: HTTP endpoint
- Ruta: /settings/audit/export
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/audit/export with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.

#### Funcion: settings_office365_email_update
- Ubicacion: app/admin.py:959
- Tipo: HTTP endpoint
- Ruta: /settings/integrations/office365-email
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /settings/integrations/office365-email with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: kb_list
- Ubicacion: app/admin.py:996
- Tipo: HTTP endpoint
- Ruta: /kb
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /kb with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires technician or administrator role.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: kb_search
- Ubicacion: app/admin.py:1021
- Tipo: HTTP endpoint
- Ruta: /kb/search
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /kb/search with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires technician or administrator role.
- Efectos principales:
  - Returns JSON response.

#### Funcion: kb_from_comment
- Ubicacion: app/admin.py:1042
- Tipo: HTTP endpoint
- Ruta: /kb/from-comment/<int:comment_id>
- Metodos HTTP: GET
- Parametros: comment_id
- Que hace: Exposes route /kb/from-comment/<int:comment_id> with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires technician or administrator role.
- Efectos principales:
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: kb_from_ticket
- Ubicacion: app/admin.py:1057
- Tipo: HTTP endpoint
- Ruta: /kb/from-ticket/<int:ticket_id>
- Metodos HTTP: GET
- Parametros: ticket_id
- Que hace: Exposes route /kb/from-ticket/<int:ticket_id> with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires technician or administrator role.
- Efectos principales:
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: kb_create
- Ubicacion: app/admin.py:1082
- Tipo: HTTP endpoint
- Ruta: /kb/create
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /kb/create with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires technician or administrator role.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: kb_edit
- Ubicacion: app/admin.py:1118
- Tipo: HTTP endpoint
- Ruta: /kb/<int:article_id>/edit
- Metodos HTTP: GET, POST
- Parametros: article_id
- Que hace: Exposes route /kb/<int:article_id>/edit with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires technician or administrator role.
- Efectos principales:
  - Persists database changes.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: kb_delete
- Ubicacion: app/admin.py:1142
- Tipo: HTTP endpoint
- Ruta: /kb/<int:article_id>/delete
- Metodos HTTP: POST
- Parametros: article_id
- Que hace: Exposes route /kb/<int:article_id>/delete with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: kb_approve
- Ubicacion: app/admin.py:1154
- Tipo: HTTP endpoint
- Ruta: /kb/<int:article_id>/approve
- Metodos HTTP: POST
- Parametros: article_id
- Que hace: Exposes route /kb/<int:article_id>/approve with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: kb_reject
- Ubicacion: app/admin.py:1168
- Tipo: HTTP endpoint
- Ruta: /kb/<int:article_id>/reject
- Metodos HTTP: POST
- Parametros: article_id
- Que hace: Exposes route /kb/<int:article_id>/reject with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires administrator privileges.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

#### Funcion: executive_report
- Ubicacion: app/admin.py:1196
- Tipo: HTTP endpoint
- Ruta: /report
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /report with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
  - Requires technician or administrator role.
- Efectos principales:
  - Renders HTML template response.

### Modulo: app/ai_chatbot.py

#### Funcion: ChatBot.__init__
- Ubicacion: app/ai_chatbot.py:178
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: ChatBot._train
- Ubicacion: app/ai_chatbot.py:185
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: ChatBot.find_answer
- Ubicacion: app/ai_chatbot.py:204
- Tipo: Class method
- Parametros: self, question
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: ChatBot.get_all_categories
- Ubicacion: app/ai_chatbot.py:253
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: ChatBot.get_entries_by_category
- Ubicacion: app/ai_chatbot.py:257
- Tipo: Class method
- Parametros: self, category
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: get_chatbot
- Ubicacion: app/ai_chatbot.py:266
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: answer_question
- Ubicacion: app/ai_chatbot.py:274
- Tipo: Application helper
- Parametros: question
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: should_auto_respond
- Ubicacion: app/ai_chatbot.py:287
- Tipo: Application helper
- Parametros: title, description, confidence_threshold
- Que hace: Provides shared application utility behavior used by multiple flows.

### Modulo: app/ai_sentiment.py

#### Funcion: SentimentAnalyzer.__init__
- Ubicacion: app/ai_sentiment.py:38
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer.analyze
- Ubicacion: app/ai_sentiment.py:44
- Tipo: Class method
- Parametros: self, text
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer._get_textblob_sentiment
- Ubicacion: app/ai_sentiment.py:90
- Tipo: Class method
- Parametros: self, text
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer._get_keyword_sentiment
- Ubicacion: app/ai_sentiment.py:106
- Tipo: Class method
- Parametros: self, text_lower
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer._label_sentiment
- Ubicacion: app/ai_sentiment.py:123
- Tipo: Class method
- Parametros: self, score
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer._analyze_urgency
- Ubicacion: app/ai_sentiment.py:136
- Tipo: Class method
- Parametros: self, text_lower
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer._build_explanation
- Ubicacion: app/ai_sentiment.py:165
- Tipo: Class method
- Parametros: self, sentiment, urgency, text_lower
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer._default_result
- Ubicacion: app/ai_sentiment.py:189
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer.get_priority_adjustment
- Ubicacion: app/ai_sentiment.py:200
- Tipo: Class method
- Parametros: self, sentiment_label
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: SentimentAnalyzer.get_urgency_adjustment
- Ubicacion: app/ai_sentiment.py:218
- Tipo: Class method
- Parametros: self, urgency_level
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: get_analyzer
- Ubicacion: app/ai_sentiment.py:239
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: analyze_ticket
- Ubicacion: app/ai_sentiment.py:247
- Tipo: Application helper
- Parametros: title, description
- Que hace: Provides shared application utility behavior used by multiple flows.

### Modulo: app/api.py

#### Funcion: _integration_config
- Ubicacion: app/api.py:20
- Tipo: Internal helper
- Parametros: integration
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: require_api_token
- Ubicacion: app/api.py:29
- Tipo: Application helper
- Parametros: f
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Persists database changes.
  - Returns JSON response.

#### Funcion: decorated_function
- Ubicacion: app/api.py:32
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Persists database changes.
  - Returns JSON response.

#### Funcion: create_ticket_api
- Ubicacion: app/api.py:61
- Tipo: HTTP endpoint
- Ruta: /tickets
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /tickets with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Rolls back transaction on error.
  - Returns JSON response.

#### Funcion: office365_email_intake
- Ubicacion: app/api.py:210
- Tipo: HTTP endpoint
- Ruta: /email/intake
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /email/intake with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Rolls back transaction on error.
  - Returns JSON response.

#### Funcion: get_ticket_api
- Ubicacion: app/api.py:271
- Tipo: HTTP endpoint
- Ruta: /tickets/<int:ticket_id>
- Metodos HTTP: GET
- Parametros: ticket_id
- Que hace: Exposes route /tickets/<int:ticket_id> with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Returns JSON response.
  - Loads resource or returns 404 automatically.

#### Funcion: slack_webhook
- Ubicacion: app/api.py:295
- Tipo: HTTP endpoint
- Ruta: /webhooks/slack
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /webhooks/slack with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Returns JSON response.

#### Funcion: teams_webhook
- Ubicacion: app/api.py:410
- Tipo: HTTP endpoint
- Ruta: /webhooks/teams
- Metodos HTTP: POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /webhooks/teams with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Returns JSON response.

### Modulo: app/api_validators.py

#### Funcion: TicketCreateSchema.process_data
- Ubicacion: app/api_validators.py:16
- Tipo: Class method
- Parametros: self, data
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketUpdateSchema.validate_status
- Ubicacion: app/api_validators.py:32
- Tipo: Class method
- Parametros: self, data
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketCommentSchema.process_data
- Ubicacion: app/api_validators.py:44
- Tipo: Class method
- Parametros: self, data
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: WebhookPayloadSchema.validate_timestamp
- Ubicacion: app/api_validators.py:59
- Tipo: Class method
- Parametros: self, data
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: PasswordChangeSchema.validate_passwords_match
- Ubicacion: app/api_validators.py:95
- Tipo: Class method
- Parametros: self, data
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: validate_request
- Ubicacion: app/api_validators.py:104
- Tipo: Application helper
- Parametros: schema_class, data
- Que hace: Provides shared application utility behavior used by multiple flows.

### Modulo: app/auth.py

#### Funcion: load_user
- Ubicacion: app/auth.py:14
- Tipo: Application helper
- Parametros: user_id
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: _t
- Ubicacion: app/auth.py:20
- Tipo: Internal helper
- Parametros: text
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: must_change_default_admin_password
- Ubicacion: app/auth.py:24
- Tipo: Application helper
- Parametros: user
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: _login_rate_limit_key
- Ubicacion: app/auth.py:35
- Tipo: Internal helper
- Parametros: sin parametros declarados
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: login
- Ubicacion: app/auth.py:45
- Tipo: HTTP endpoint
- Ruta: /login
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /login with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: force_password_change
- Ubicacion: app/auth.py:99
- Tipo: HTTP endpoint
- Ruta: /force-password-change
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /force-password-change with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Persists database changes.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: change_password
- Ubicacion: app/auth.py:137
- Tipo: HTTP endpoint
- Ruta: /change-password
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /change-password with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Persists database changes.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: verify_totp
- Ubicacion: app/auth.py:183
- Tipo: HTTP endpoint
- Ruta: /verify-2fa
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /verify-2fa with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Persists database changes.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: logout
- Ubicacion: app/auth.py:227
- Tipo: HTTP endpoint
- Ruta: /logout
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /logout with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: register
- Ubicacion: app/auth.py:234
- Tipo: HTTP endpoint
- Ruta: /register
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /register with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Can terminate request with HTTP error code.

### Modulo: app/forms.py

#### Funcion: tr
- Ubicacion: app/forms.py:11
- Tipo: Application helper
- Parametros: en_text, es_text
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: LoginForm.__init__
- Ubicacion: app/forms.py:21
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketForm.__init__
- Ubicacion: app/forms.py:38
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketUpdateForm.__init__
- Ubicacion: app/forms.py:64
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: CSATForm.__init__
- Ubicacion: app/forms.py:87
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: UserRoleForm.__init__
- Ubicacion: app/forms.py:98
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: company_email
- Ubicacion: app/forms.py:105
- Tipo: Application helper
- Parametros: form, field
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: NewUserForm.__init__
- Ubicacion: app/forms.py:122
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: NewUserForm.validate_username
- Ubicacion: app/forms.py:131
- Tipo: Class method
- Parametros: self, field
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: NewUserForm.validate_email
- Ubicacion: app/forms.py:136
- Tipo: Class method
- Parametros: self, field
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketOptionForm.__init__
- Ubicacion: app/forms.py:147
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketOptionForm.validate_value
- Ubicacion: app/forms.py:155
- Tipo: Class method
- Parametros: self, field
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: ForcePasswordChangeForm.__init__
- Ubicacion: app/forms.py:166
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: AdminResetPasswordForm.__init__
- Ubicacion: app/forms.py:178
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: ChangePasswordForm.__init__
- Ubicacion: app/forms.py:191
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

### Modulo: app/ml_classifier.py

#### Funcion: TicketClassifier.__init__
- Ubicacion: app/ml_classifier.py:35
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketClassifier._prepare_features
- Ubicacion: app/ml_classifier.py:48
- Tipo: Class method
- Parametros: self, tickets_data
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketClassifier.train
- Ubicacion: app/ml_classifier.py:89
- Tipo: Class method
- Parametros: self, min_tickets
- Que hace: Implements model/business behavior encapsulated in class logic.
- Efectos principales:
  - Persists database changes.

#### Funcion: TicketClassifier.predict
- Ubicacion: app/ml_classifier.py:182
- Tipo: Class method
- Parametros: self, ticket_data, top_n
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketClassifier._update_technician_stats
- Ubicacion: app/ml_classifier.py:237
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.

#### Funcion: TicketClassifier.save_model
- Ubicacion: app/ml_classifier.py:288
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketClassifier.load_model
- Ubicacion: app/ml_classifier.py:309
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TicketClassifier.get_model_info
- Ubicacion: app/ml_classifier.py:332
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

### Modulo: app/ml_commands.py

#### Funcion: register_ml_commands
- Ubicacion: app/ml_commands.py:10
- Tipo: Application helper
- Parametros: app
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: train_model
- Ubicacion: app/ml_commands.py:15
- Tipo: Application helper
- Parametros: min_tickets
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: model_info
- Ubicacion: app/ml_commands.py:42
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: technician_stats
- Ubicacion: app/ml_commands.py:67
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

### Modulo: app/models.py

#### Funcion: utcnow
- Ubicacion: app/models.py:11
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: User.set_password
- Ubicacion: app/models.py:36
- Tipo: Class method
- Parametros: self, password
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: User.check_password
- Ubicacion: app/models.py:40
- Tipo: Class method
- Parametros: self, password
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: User.is_admin
- Ubicacion: app/models.py:43
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: User.is_technician
- Ubicacion: app/models.py:46
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: User.is_account_locked
- Ubicacion: app/models.py:49
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.
- Efectos principales:
  - Persists database changes.

#### Funcion: User.record_failed_login
- Ubicacion: app/models.py:61
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.
- Efectos principales:
  - Persists database changes.

#### Funcion: User.reset_failed_login
- Ubicacion: app/models.py:72
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.
- Efectos principales:
  - Persists database changes.

#### Funcion: Ticket.default_categories
- Ubicacion: app/models.py:117
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.default_priorities
- Ubicacion: app/models.py:121
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.categories
- Ubicacion: app/models.py:125
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.priorities
- Ubicacion: app/models.py:139
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.statuses
- Ubicacion: app/models.py:153
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.sla_hours_by_priority
- Ubicacion: app/models.py:162
- Tipo: Class method
- Parametros: priority
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.is_closed
- Ubicacion: app/models.py:171
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.sla_warning_window_hours
- Ubicacion: app/models.py:174
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.is_overdue
- Ubicacion: app/models.py:179
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: Ticket.is_due_soon
- Ubicacion: app/models.py:182
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: ApiToken.is_valid
- Ubicacion: app/models.py:279
- Tipo: Class method
- Parametros: self
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: AuditLog.log_action
- Ubicacion: app/models.py:319
- Tipo: Class method
- Parametros: user_id, action, resource_type, resource_id, ip_address, user_agent, status, details
- Que hace: Implements model/business behavior encapsulated in class logic.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Rolls back transaction on error.

#### Funcion: PasswordHistory.check_password_reuse
- Ubicacion: app/models.py:350
- Tipo: Class method
- Parametros: user_id, password, max_history
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: PasswordHistory.add_to_history
- Ubicacion: app/models.py:364
- Tipo: Class method
- Parametros: user_id, password_hash, commit
- Que hace: Implements model/business behavior encapsulated in class logic.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.

### Modulo: app/routes.py

#### Funcion: index
- Ubicacion: app/routes.py:8
- Tipo: HTTP endpoint
- Ruta: /
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route / with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: health_check
- Ubicacion: app/routes.py:13
- Tipo: HTTP endpoint
- Ruta: /health
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /health with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Returns JSON response.

#### Funcion: presence_ping
- Ubicacion: app/routes.py:20
- Tipo: HTTP endpoint
- Ruta: /presence-ping
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /presence-ping with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.

#### Funcion: set_language
- Ubicacion: app/routes.py:26
- Tipo: HTTP endpoint
- Ruta: /lang/<lang>
- Metodos HTTP: GET
- Parametros: lang
- Que hace: Exposes route /lang/<lang> with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Redirects browser to another route.

#### Funcion: about_us
- Ubicacion: app/routes.py:34
- Tipo: HTTP endpoint
- Ruta: /quienes-somos
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /quienes-somos with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Renders HTML template response.

#### Funcion: terms_and_conditions
- Ubicacion: app/routes.py:39
- Tipo: HTTP endpoint
- Ruta: /terminos-y-condiciones
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /terminos-y-condiciones with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Efectos principales:
  - Renders HTML template response.

### Modulo: app/schema_sync.py

#### Funcion: _ensure_columns
- Ubicacion: app/schema_sync.py:46
- Tipo: Internal helper
- Parametros: table_name, columns
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.
- Efectos principales:
  - Persists database changes.

#### Funcion: ensure_runtime_schema
- Ubicacion: app/schema_sync.py:60
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.
- Efectos principales:
  - Rolls back transaction on error.

### Modulo: app/security.py

#### Funcion: PasswordValidator.validate
- Ubicacion: app/security.py:47
- Tipo: Class method
- Parametros: password
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TOTPManager.generate_secret
- Ubicacion: app/security.py:88
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TOTPManager.generate_totp
- Ubicacion: app/security.py:93
- Tipo: Class method
- Parametros: secret
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TOTPManager.get_provisioning_uri
- Ubicacion: app/security.py:98
- Tipo: Class method
- Parametros: secret, name, issuer
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TOTPManager.get_qr_code_svg
- Ubicacion: app/security.py:107
- Tipo: Class method
- Parametros: provisioning_uri
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TOTPManager.verify_token
- Ubicacion: app/security.py:128
- Tipo: Class method
- Parametros: secret, token
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TOTPManager.generate_backup_codes
- Ubicacion: app/security.py:138
- Tipo: Class method
- Parametros: count
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: TOTPManager.verify_backup_code
- Ubicacion: app/security.py:144
- Tipo: Class method
- Parametros: codes_str, code
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: FileSecurityValidator.validate
- Ubicacion: app/security.py:172
- Tipo: Class method
- Parametros: file_storage
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: FileSecurityValidator._detect_mime_type
- Ubicacion: app/security.py:221
- Tipo: Class method
- Parametros: file_header, filename
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: FileSecurityValidator.scan_for_malware
- Ubicacion: app/security.py:250
- Tipo: Class method
- Parametros: file_path
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: AuditHelper.get_client_ip
- Ubicacion: app/security.py:285
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: AuditHelper.get_user_agent
- Ubicacion: app/security.py:292
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: AuditHelper.log_login_attempt
- Ubicacion: app/security.py:297
- Tipo: Class method
- Parametros: user, success, ip_address, user_agent
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: AuditHelper.log_password_change
- Ubicacion: app/security.py:317
- Tipo: Class method
- Parametros: user_id, ip_address, user_agent
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: AuditHelper.log_2fa_setup
- Ubicacion: app/security.py:336
- Tipo: Class method
- Parametros: user_id, enabled, ip_address, user_agent
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: AuditHelper.log_ticket_action
- Ubicacion: app/security.py:355
- Tipo: Class method
- Parametros: user_id, action, ticket_id, ip_address, user_agent
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: EncryptionManager.get_cipher
- Ubicacion: app/security.py:378
- Tipo: Class method
- Parametros: sin parametros declarados
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: EncryptionManager.encrypt
- Ubicacion: app/security.py:400
- Tipo: Class method
- Parametros: data
- Que hace: Implements model/business behavior encapsulated in class logic.

#### Funcion: EncryptionManager.decrypt
- Ubicacion: app/security.py:413
- Tipo: Class method
- Parametros: encrypted_data
- Que hace: Implements model/business behavior encapsulated in class logic.

### Modulo: app/tickets.py

#### Funcion: utcnow
- Ubicacion: app/tickets.py:20
- Tipo: Application helper
- Parametros: sin parametros declarados
- Que hace: Provides shared application utility behavior used by multiple flows.

#### Funcion: _t
- Ubicacion: app/tickets.py:25
- Tipo: Internal helper
- Parametros: text
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: _ticket_read_access
- Ubicacion: app/tickets.py:29
- Tipo: Internal helper
- Parametros: ticket
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: _ticket_chat_access
- Ubicacion: app/tickets.py:33
- Tipo: Internal helper
- Parametros: ticket
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: _serialize_comment
- Ubicacion: app/tickets.py:41
- Tipo: Internal helper
- Parametros: ticket, comment
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: _safe_datetime_text
- Ubicacion: app/tickets.py:59
- Tipo: Internal helper
- Parametros: value, fmt
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: _ticket_timeline
- Ubicacion: app/tickets.py:63
- Tipo: Internal helper
- Parametros: ticket
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: _reopen_deadline
- Ubicacion: app/tickets.py:97
- Tipo: Internal helper
- Parametros: ticket
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: _can_reopen_ticket
- Ubicacion: app/tickets.py:106
- Tipo: Internal helper
- Parametros: ticket
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: handle_connect
- Ubicacion: app/tickets.py:114
- Tipo: Socket event
- Parametros: sin parametros declarados
- Que hace: Handles a real-time Socket.IO event for chat/presence synchronization.

#### Funcion: handle_join_ticket_room
- Ubicacion: app/tickets.py:152
- Tipo: Socket event
- Parametros: data
- Que hace: Handles a real-time Socket.IO event for chat/presence synchronization.

#### Funcion: handle_disconnect
- Ubicacion: app/tickets.py:174
- Tipo: Socket event
- Parametros: sin parametros declarados
- Que hace: Handles a real-time Socket.IO event for chat/presence synchronization.

#### Funcion: handle_ticket_chat_message
- Ubicacion: app/tickets.py:194
- Tipo: Socket event
- Parametros: data
- Que hace: Handles a real-time Socket.IO event for chat/presence synchronization.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.

#### Funcion: _attachments_dir
- Ubicacion: app/tickets.py:213
- Tipo: Internal helper
- Parametros: sin parametros declarados
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.

#### Funcion: _save_attachment
- Ubicacion: app/tickets.py:232
- Tipo: Internal helper
- Parametros: file_storage, ticket_id
- Que hace: Supports internal workflow orchestration and is not intended as public endpoint.
- Efectos principales:
  - Creates or stages new records in database session.

#### Funcion: list_tickets
- Ubicacion: app/tickets.py:284
- Tipo: HTTP endpoint
- Ruta: /
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route / with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Renders HTML template response.
  - Sends user-visible feedback message.

#### Funcion: create_ticket
- Ubicacion: app/tickets.py:450
- Tipo: HTTP endpoint
- Ruta: /create
- Metodos HTTP: GET, POST
- Parametros: sin parametros declarados
- Que hace: Exposes route /create with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: kb_suggestions
- Ubicacion: app/tickets.py:503
- Tipo: HTTP endpoint
- Ruta: /kb-suggestions
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /kb-suggestions with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Returns JSON response.

#### Funcion: request_password_reset_ticket
- Ubicacion: app/tickets.py:525
- Tipo: HTTP endpoint
- Ruta: /request-password-reset
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /request-password-reset with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Sends user-visible feedback message.
  - Redirects browser to another route.

#### Funcion: download_attachment
- Ubicacion: app/tickets.py:581
- Tipo: HTTP endpoint
- Ruta: /attachments/<int:attachment_id>/download
- Metodos HTTP: GET
- Parametros: attachment_id
- Que hace: Exposes route /attachments/<int:attachment_id>/download with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Loads resource or returns 404 automatically.
  - Can terminate request with HTTP error code.

#### Funcion: export_tickets
- Ubicacion: app/tickets.py:598
- Tipo: HTTP endpoint
- Ruta: /export
- Metodos HTTP: GET
- Parametros: sin parametros declarados
- Que hace: Exposes route /export with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.

#### Funcion: ticket_detail
- Ubicacion: app/tickets.py:681
- Tipo: HTTP endpoint
- Ruta: /<int:ticket_id>
- Metodos HTTP: GET, POST
- Parametros: ticket_id
- Que hace: Exposes route /<int:ticket_id> with HTTP methods GET, POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Renders HTML template response.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Broadcasts real-time event via Socket.IO.
  - Redirects browser to another route.

#### Funcion: reopen_ticket
- Ubicacion: app/tickets.py:777
- Tipo: HTTP endpoint
- Ruta: /<int:ticket_id>/reopen
- Metodos HTTP: POST
- Parametros: ticket_id
- Que hace: Exposes route /<int:ticket_id>/reopen with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Persists database changes.
  - Creates or stages new records in database session.
  - Sends user-visible feedback message.
  - Triggers email notification flow.
  - Loads resource or returns 404 automatically.
  - Can terminate request with HTTP error code.
  - Redirects browser to another route.

#### Funcion: submit_csat
- Ubicacion: app/tickets.py:836
- Tipo: HTTP endpoint
- Ruta: /<int:ticket_id>/csat
- Metodos HTTP: POST
- Parametros: ticket_id
- Que hace: Exposes route /<int:ticket_id>/csat with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Persists database changes.
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Can terminate request with HTTP error code.
  - Redirects browser to another route.

#### Funcion: ticket_chat_feed
- Ubicacion: app/tickets.py:863
- Tipo: HTTP endpoint
- Ruta: /<int:ticket_id>/chat-feed
- Metodos HTTP: GET
- Parametros: ticket_id
- Que hace: Exposes route /<int:ticket_id>/chat-feed with HTTP methods GET. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Returns JSON response.
  - Loads resource or returns 404 automatically.

#### Funcion: delete_ticket
- Ubicacion: app/tickets.py:876
- Tipo: HTTP endpoint
- Ruta: /<int:ticket_id>/delete
- Metodos HTTP: POST
- Parametros: ticket_id
- Que hace: Exposes route /<int:ticket_id>/delete with HTTP methods POST. Handles web request lifecycle and returns UI/API output.
- Seguridad/Permisos:
  - Requires authenticated session.
- Efectos principales:
  - Sends user-visible feedback message.
  - Loads resource or returns 404 automatically.
  - Redirects browser to another route.

## 5. Notas operativas
- Revisar POST_LAUNCH_CHECKLIST.md para validacion post despliegue.
- Para regenerar este manual, ejecutar tools/generate_detailed_manual.py y luego tools/build_manual_pdf.py.

Fin del documento.
