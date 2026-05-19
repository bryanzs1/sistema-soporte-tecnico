# Manual Profesional de Funcionalidades del Sistema

## 1. Presentacion
Documento oficial del sistema de soporte tecnico orientado a operacion funcional. Este manual describe que hace el sistema y como se utiliza por rol, sin detalle de codigo fuente.

- Version del manual: 2.1
- Fecha de generacion: 2026-03-11
- Enfoque: funcionalidades de negocio y operacion

## 2. Publico objetivo
- Direccion/Operacion: comprension de capacidades y controles del sistema.
- Soporte tecnico: uso diario de flujos y validaciones.
- Lideres de area: seguimiento de indicadores y calidad de servicio.

## 3. Roles del sistema
- Usuario: crea, consulta, comenta, califica y reabre tickets dentro de la ventana permitida.
- Tecnico: gestiona flujo operativo de tickets, chat y conocimientos.
- Administrador: gestiona configuracion, seguridad, usuarios, integraciones, auditoria y reportes.

## 4. Funcionalidades principales
- Gestion integral de tickets: creacion, asignacion, seguimiento, cierre y reapertura controlada.
- Comunicacion integrada: comentarios y chat en tiempo real entre usuario y equipo tecnico.
- Base de conocimiento: consulta de articulos y sugerencias automaticas durante la creacion de tickets.
- Control de servicio: estado operativo, indicadores SLA, satisfaccion del usuario y reportes ejecutivos.
- Gobierno y seguridad: control de acceso por rol, confirmaciones para acciones criticas, auditoria e integraciones empresariales.

## 5. Flujo funcional de tickets
1. Registro del caso: el usuario crea un ticket con categoria, prioridad y descripcion del incidente.
2. Analisis inicial: el sistema enruta el caso y el equipo tecnico prioriza atencion segun severidad.
3. Atencion y colaboracion: se intercambian mensajes, evidencias y actualizaciones de avance.
4. Resolucion: el tecnico documenta solucion, aplica cierre y deja trazabilidad del proceso.
5. Validacion del usuario: el usuario confirma resultado y registra calificacion de satisfaccion.
6. Reapertura controlada: si persiste la incidencia, se habilita reapertura con motivo dentro del plazo permitido.

## 6. Funcionalidades por rol
### 6.1 Usuario
- Crear tickets y adjuntar informacion del incidente.
- Consultar estado y progreso en su panel.
- Enviar comentarios y responder en el chat del caso.
- Reabrir tickets con motivo cuando aplique.
- Calificar la atencion recibida al cierre del servicio.

### 6.2 Tecnico
- Visualizar cola de tickets por prioridad y estado.
- Tomar, actualizar y cerrar casos con trazabilidad.
- Mantener comunicacion continua con el solicitante.
- Consultar respuestas rapidas y base de conocimiento para resolver mas rapido.
- Gestionar reaperturas y cumplimiento de tiempos de atencion.

### 6.3 Administrador
- Administrar usuarios, perfiles y permisos.
- Configurar parametros del sistema, politicas y plantillas operativas.
- Supervisar auditoria, actividad sensible e integraciones.
- Revisar indicadores de servicio, cumplimiento y calidad.
- Coordinar mejoras continuas sobre procesos de soporte.

## 7. Seguridad y control
- Acceso controlado por autenticacion y roles.
- Confirmaciones reforzadas para acciones criticas.
- Registro de eventos para trazabilidad y auditoria.
- Politicas de sesion y validacion para reducir errores operativos.

## 8. Indicadores y seguimiento
- Seguimiento de tiempos de atencion y cumplimiento de SLA.
- Medicion de satisfaccion de usuario y calidad de resolucion.
- Vista ejecutiva para monitoreo de volumen, estado y tendencia de casos.

## 9. Herramientas del proyecto y su funcion
- Python: lenguaje base para logica de negocio y servicios backend.
- Flask: framework web principal para rutas, vistas y ciclo de solicitudes.
- Flask-SQLAlchemy: capa ORM para modelado y acceso a datos.
- Flask-Migrate: control de migraciones de esquema de base de datos.
- Flask-Login: autenticacion de sesiones y control de usuario activo.
- Flask-WTF: formularios con validaciones y proteccion CSRF.
- Flask-Limiter: limitacion de intentos para proteger endpoints sensibles.
- Flask-Talisman: endurecimiento de cabeceras de seguridad HTTP.
- Flask-CORS: control de acceso entre origenes para integraciones web/API.
- Flask-Mail: envio de notificaciones por correo.
- Flask-SocketIO: comunicacion en tiempo real para chat y eventos operativos.
- eventlet: soporte de concurrencia para Socket.IO en produccion.
- redis: backend de mensajeria/cache para eventos y escalabilidad.
- psycopg2-binary: conector PostgreSQL para persistencia en entorno productivo.
- gunicorn: servidor WSGI de ejecucion en despliegues Linux/Render.
- python-dotenv: carga de variables de entorno desde archivo .env.
- pyotp: generacion y validacion de codigos TOTP para 2FA.
- qrcode y pillow: generacion de imagen QR para enrolamiento 2FA.
- sentry-sdk: monitoreo de errores y telemetria de excepciones.
- marshmallow: serializacion y validacion de estructuras de datos.
- cryptography: cifrado y operaciones criptograficas de soporte.
- requests: consumo de APIs externas y validaciones de conectividad.
- beautifulsoup4: parsing HTML en utilidades de integracion/analisis.
- pandas: analisis tabular para reportes y consolidaciones.
- scikit-learn y numpy: capacidades de analitica/modelado en componentes inteligentes.
- textblob: apoyo NLP para procesamiento de texto y clasificacion basica.

## 10. Notas operativas
- Revisar POST_LAUNCH_CHECKLIST.md para validacion post despliegue.
- Regeneracion del documento: ejecutar tools/generate_detailed_manual.py y luego tools/build_manual_pdf.py.

Documento funcional del sistema (sin detalle tecnico de codigo).
