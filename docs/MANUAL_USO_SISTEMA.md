# Manual de Uso Completo

## 1. Introduccion
Este documento describe el uso funcional y operativo del sistema de soporte tecnico para los tres perfiles principales: usuario, tecnico y administrador.

Objetivo:
- Entender como usar cada modulo.
- Reducir errores operativos.
- Estandarizar el flujo de atencion.

---

## 2. Roles y Permisos

### 2.1 Usuario
Puede:
- Iniciar sesion.
- Crear tickets.
- Ver sus propios tickets.
- Comentar en sus tickets.
- Adjuntar archivos.
- Calificar la atencion (CSAT) cuando el ticket esta cerrado.
- Reabrir tickets cerrados (con motivo y dentro de ventana permitida).

No puede:
- Ver tickets de otros usuarios.
- Gestionar usuarios.
- Cambiar configuraciones de sistema.

### 2.2 Tecnico
Puede:
- Ver todos los tickets.
- Responder en chat de tickets asignados.
- Cambiar estado de tickets.
- Asignarse o reasignar tickets segun permisos del formulario.
- Usar Base de Conocimiento (KB).
- Usar respuestas rapidas en chat.

No puede:
- Gestionar usuarios administradores.
- Acceder a configuraciones exclusivas de admin.

### 2.3 Administrador
Puede:
- Todo lo del tecnico.
- Gestionar usuarios y roles.
- Gestionar categorias/prioridades.
- Gestionar integraciones y tokens API.
- Revisar auditoria y exportarla.
- Gestionar configuraciones de IA/ML.
- Aprobar/rechazar articulos de KB.
- Ver dashboard ejecutivo y reportes.

---

## 3. Flujo General de Soporte

1. Usuario crea ticket.
2. Sistema asigna SLA segun prioridad.
3. Tecnico/admin toma ticket y actualiza estado.
4. Interaccion via chat interno del ticket.
5. Ticket se cierra al resolver.
6. Usuario puede calificar (CSAT).
7. Si aplica, usuario/tecnico/admin reabre con motivo.

---

## 4. Modulo de Autenticacion

Rutas principales:
- /auth/login
- /auth/logout
- /auth/change-password
- /auth/verify-2fa

Funciones clave:
- Control de intentos de login.
- Validaciones de seguridad de password.
- Confirmacion de cierre de sesion para evitar clic accidental.

Buenas practicas:
- No compartir credenciales.
- Activar y usar 2FA si esta habilitado.

---

## 5. Modulo de Tickets (Usuario y Tecnico)

Rutas principales:
- /tickets/
- /tickets/create
- /tickets/<id>
- /tickets/<id>/reopen
- /tickets/export
- /tickets/kb-suggestions

### 5.1 Crear Ticket
Campos recomendados:
- Nombre del solicitante.
- Categoria correcta.
- Titulo claro.
- Descripcion detallada.
- Prioridad real.
- Adjuntos cuando aplique.

Novedad:
- Sugerencias de KB en tiempo real al escribir descripcion.

### 5.2 Listado de Tickets
Incluye:
- Filtros por estado, categoria, prioridad, fechas y palabra clave.
- Priorizacion por SLA.
- Exportacion CSV/XLSX.

### 5.3 Detalle del Ticket
Incluye:
- Estado, prioridad, SLA y datos del solicitante.
- Timeline de eventos.
- Chat directo.
- Adjuntos.
- Formulario de actualizacion para tecnico/admin.

### 5.4 Reapertura de Ticket
Reglas:
- Solo tickets cerrados.
- Debe existir motivo de reapertura.
- Ventana maxima de reapertura: 7 dias desde cierre.

Automatizacion:
- Se registra comentario con motivo.
- Se notifica por correo a solicitante y tecnico asignado (si tienen email).

### 5.5 Confirmaciones Fuertes
Para evitar errores:
- Cerrar ticket requiere escribir CERRAR.
- Revocar token API requiere escribir REVOCAR.
- Navegacion con cambios no guardados muestra advertencia.

---

## 6. Chat Operativo y Colaboracion

En detalle del ticket:
- Chat en tiempo real con Socket.IO.
- Respuestas rapidas para tecnico/admin.
- Insercion de contenido desde KB.

Objetivo:
- Reducir tiempos de respuesta.
- Estandarizar comunicacion con usuario.

---

## 7. Base de Conocimiento (KB)

Rutas:
- /admin/kb
- /admin/kb/create
- /admin/kb/<id>/edit
- /admin/kb/<id>/approve
- /admin/kb/<id>/reject
- /admin/kb/search

Capacidades:
- Crear articulos manualmente.
- Crear articulo desde comentario o ticket cerrado.
- Flujo de aprobacion/rechazo.
- Busqueda para insercion en chat y sugerencias en creacion de ticket.

---

## 8. Dashboard y Reporte Ejecutivo

Rutas:
- /admin/dashboard
- /admin/report

Indicadores principales:
- Total abiertos/cerrados.
- Vencidos SLA y por vencer.
- CSAT promedio.
- Cumplimiento SLA.
- Tickets reabiertos.

Uso recomendado:
- Seguimiento diario operativo.
- Reporte semanal de gestion.

---

## 9. Integraciones y API

### 9.1 API Tokens
Rutas:
- /admin/integrations/tokens/create
- /admin/integrations/tokens/<id>/revoke

### 9.2 Webhooks / API
Rutas:
- /api/v1/tickets (POST)
- /api/v1/tickets/<id> (GET)
- /api/v1/webhooks/slack
- /api/v1/webhooks/teams
- /api/v1/email/intake (Office 365)

### 9.3 Seguridad Operativa
- Revocacion de tokens con confirmacion fuerte.
- Posibilidad de restringir remitentes en intake de correo.

---

## 10. Auditoria y Trazabilidad

Rutas:
- /admin/settings/audit
- /admin/settings/audit/export

Registra:
- Acciones sensibles.
- Errores de carga de listados/queries.
- Eventos de seguridad.

Objetivo:
- Analisis de incidentes.
- Evidencia operativa/compliance.

---

## 11. Configuracion del Sistema

Centro de configuracion:
- /admin/settings

Submodulos:
- Usuarios.
- Ticket options.
- IA y ML.
- Integraciones.
- Auditoria.

---

## 12. IA y ML

Funciones:
- Sugerencia de tecnico por modelo ML.
- Autoasignacion en confianza alta.
- Analisis de sentimiento/urgencia.
- Respuesta automatica basada en conocimiento.

Rutas relacionadas:
- /admin/ml-system
- /admin/ml-system/train
- /admin/ai-system
- /admin/ai-system/settings

---

## 13. Politicas de Seguridad Implementadas

- Eliminacion de tickets bloqueada por politica.
- Confirmaciones para acciones criticas.
- Advertencia por cambios no guardados.
- Validacion de archivos adjuntos.
- Registro de auditoria.

---

## 14. Errores Comunes y Solucion Rapida

### 14.1 No veo tickets pero dashboard muestra conteo
Accion:
- Revisar /admin/settings/audit por eventos de error de query.

### 14.2 No aparece opcion en configuracion
Accion:
- Verificar ruta en menu de settings y deploy activo.

### 14.3 No llegan sugerencias KB
Accion:
- Confirmar que existan articulos activos y texto >= 3 caracteres.

### 14.4 No permite reabrir
Accion:
- Verificar que ticket este Cerrado y no haya vencido ventana de 7 dias.

---

## 15. Checklist Operativo Recomendado

Usar:
- POST_LAUNCH_CHECKLIST.md

Aplicacion:
- Verificacion de salud, smoke tests, notificaciones, seguridad y rollback.

---

## 16. Resumen para Capacitacion

### Usuario
- Crear ticket bien documentado.
- Revisar respuestas en chat.
- Calificar y reabrir si aplica.

### Tecnico
- Tomar tickets por SLA.
- Usar respuestas rapidas y KB.
- Cerrar con confirmacion fuerte y trazabilidad.

### Admin
- Control de usuarios y seguridad.
- Integraciones/API.
- Reportes y auditoria.

---

## 17. Anexos (Rutas principales por modulo)

### Main
- /
- /health
- /presence-ping
- /lang/<lang>
- /quienes-somos
- /terminos-y-condiciones

### Auth
- /auth/login
- /auth/logout
- /auth/change-password
- /auth/force-password-change
- /auth/verify-2fa

### Tickets
- /tickets/
- /tickets/create
- /tickets/<id>
- /tickets/<id>/reopen
- /tickets/<id>/csat
- /tickets/<id>/chat-feed
- /tickets/export
- /tickets/kb-suggestions

### Admin
- /admin/dashboard
- /admin/users
- /admin/settings
- /admin/settings/audit
- /admin/kb
- /admin/report
- /admin/integrations

### API
- /api/v1/tickets
- /api/v1/tickets/<id>
- /api/v1/webhooks/slack
- /api/v1/webhooks/teams
- /api/v1/email/intake

---

Fin del manual.
