from flask import Flask, current_app, session, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_cors import CORS
from flask_socketio import SocketIO

# Ensure eventlet monkey patching is applied (defensive, in case wsgi.py hasn't yet)
try:
    import eventlet
    if not hasattr(eventlet, '_patched'):
        eventlet.monkey_patch(all=True)
        eventlet._patched = True
except Exception:
    pass

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from dotenv import load_dotenv
import os
import logging
import hashlib
from logging.handlers import RotatingFileHandler
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# extensions

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
# default login view; must match the endpoint name in auth blueprint
login.login_view = 'auth.login'  # redirects unauthorized users to /auth/login

mail = Mail()


def _rate_limit_key():
    """Use real client IP behind reverse proxies (Render) before fallback."""
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return get_remote_address()


limiter = Limiter(key_func=_rate_limit_key)
talisman = Talisman()
cors = CORS()
socketio = SocketIO(async_mode='eventlet')

# Global registry of online users: {user_id: {'username': str, 'joined_at': datetime}}
online_users = {}


TRANSLATIONS = {
    'es': {
        'Support': 'Soporte',
        'Tickets': 'Tickets',
        'Dashboard': 'Panel',
        'Admin': 'Admin',
        'Settings': 'Configuración',
        'Logout': 'Cerrar sesión',
        'Login': 'Iniciar sesión',
        'Language': 'Idioma',
        'English': 'Inglés',
        'Spanish': 'Español',
        'Welcome to the support system': 'Bienvenido al sistema de soporte',
        'Use navigation to sign in or create tickets.': 'Use la navegación para entrar o crear tickets.',
        'Invalid username or password': 'Usuario o contraseña inválidos',
        'Ticket created successfully': 'Ticket creado correctamente',
        'You do not have access to this ticket': 'No tienes acceso a este ticket',
        'Ticket updated': 'Ticket actualizado',
        'Administrator access required': 'Se requiere acceso de administrador',
        'Technician or admin access required': 'Se requiere acceso de técnico o administrador',
        'User created': 'Usuario creado',
        'User updated': 'Usuario actualizado',
        'pandas required for excel export': 'Se requiere pandas para exportar a Excel',
        'New ticket created': 'Nuevo ticket creado',
        'Your ticket was updated': 'Tu ticket fue actualizado',
        'Ticket "{title}" has been created by {username}.': 'El ticket "{title}" fue creado por {username}.',
        'Your ticket "{title}" status is now {status}.': 'El estado de tu ticket "{title}" ahora es {status}.',
        'All statuses': 'Todos los estados',
        'All categories': 'Todas las categorías',
        'All priorities': 'Todas las prioridades',
        'From': 'Desde',
        'To': 'Hasta',
        'Search...': 'Buscar...',
        'Filter': 'Filtrar',
        'Export CSV': 'Exportar CSV',
        'Export XLSX': 'Exportar XLSX',
        'New Ticket': 'Nuevo Ticket',
        'Creator': 'Creador',
        'View': 'Ver',
        'View Details': 'Ver detalles',
        'Create a new ticket': 'Crear un nuevo ticket',
        'Status': 'Estado',
        'Priority': 'Prioridad',
        'Category': 'Categoría',
        'Description': 'Descripción',
        'Categories': 'Categorías',
        'Priorities': 'Prioridades',
        'Delete': 'Eliminar',
        'Type': 'Tipo',
        'Value': 'Valor',
        'Add': 'Agregar',
        'Ticket options': 'Opciones de ticket',
        'Manage ticket options': 'Gestionar opciones de ticket',
        'No categories configured': 'No hay categorías configuradas',
        'No priorities configured': 'No hay prioridades configuradas',
        'Option added': 'Opción agregada',
        'Option removed': 'Opción eliminada',
        'Option updated': 'Opción actualizada',
        'Option already exists': 'La opción ya existe',
        'Option already existed and was reactivated': 'La opción ya existía y fue reactivada',
        'Value is required': 'El valor es obligatorio',
        'Update': 'Actualizar',
        'Created by': 'Creado por',
        'Assigned technician': 'Técnico asignado',
        'Update ticket': 'Actualizar ticket',
        'Users': 'Usuarios',
        'Username': 'Usuario',
        'Email': 'Correo',
        'Create User': 'Crear usuario',
        'Role': 'Rol',
        'Actions': 'Acciones',
        'Action': 'Acción',
        'ID': 'ID',
        'SLA': 'SLA',
        'SLA Due': 'Vencimiento SLA',
        'Overdue': 'Vencido',
        'Due soon': 'Por vencer',
        'On time': 'En tiempo',
        'No tickets found': 'No se encontraron tickets',
        'Tickets approaching SLA deadline': 'Tickets próximos a vencer SLA',
        'SLA Compliance': 'Cumplimiento SLA',
        'Closed tickets resolved on time': 'Tickets cerrados resueltos a tiempo',
        'CSAT avg': 'CSAT prom.',
        'Average user satisfaction (1–5)': 'Satisfacción promedio del usuario (1–5)',
        'Rate your experience': 'Califica tu experiencia',
        'How was the support experience? Your feedback helps us improve.': '¿Cómo fue la experiencia de soporte? Tu opinión nos ayuda a mejorar.',
        'stars': 'estrellas',
        'Submit rating': 'Enviar calificación',
        'Thank you for your feedback!': '¡Gracias por tu comentario!',
        'Your rating': 'Tu calificación',
        'You can only rate closed tickets': 'Solo puedes calificar tickets cerrados',
        'You have already submitted a rating for this ticket': 'Ya enviaste una calificación para este ticket',
        'Please select a valid rating': 'Por favor selecciona una calificación válida',
        'Escalation Alert': 'Alerta de Escalamiento',
        'This ticket has exceeded its SLA deadline.': 'Este ticket ha superado el plazo de SLA.',
        'No technician is assigned — assign one immediately.': 'No hay técnico asignado — asigne uno de inmediato.',
        'SLA deadline is approaching and no technician is assigned.': 'El plazo de SLA se acerca y no hay técnico asignado.',
        'Comments': 'Comentarios',
        'Reopened': 'Reabierto',
        'time(s)': 'vez/veces',
        'Attachments': 'Adjuntos',
        'Download': 'Descargar',
        'No attachments': 'Sin adjuntos',
        'User': 'Usuario',
        'No comments yet': 'Aún no hay comentarios',
        'Error': 'Error',
        'An unexpected error occurred': 'Ocurrió un error inesperado al procesar la solicitud',
        'Try again. If the problem persists, notify the administrator.': 'Intenta nuevamente. Si el problema continúa, avisa al administrador.',
        'Back to tickets': 'Volver a tickets',
        'Overdue SLA': 'SLA vencidos',
        'Avg resolution (h)': 'Promedio resolución (h)',
        'Reopened tickets': 'Tickets reabiertos',
        'Attachment': 'Adjunto',
        'Comment': 'Comentario',
        'Add comment': 'Agregar comentario',
        'Repeat Password': 'Repetir contraseña',
        'Update Ticket': 'Actualizar ticket',
        'Edit': 'Editar',
        'Edit User': 'Editar usuario',
        'Create new user': 'Crear nuevo usuario',
        'Password': 'Contraseña',
        'Remember Me': 'Recordarme',
        'Sign In': 'Entrar',
        'Save': 'Guardar',
        'Assign to': 'Asignar a',
        'Your name': 'Tu nombre',
        'Title': 'Título',
        'Create Ticket': 'Crear ticket',
        'Control Panel': 'Panel de control',
        'Total tickets': 'Total de tickets',
        'Open': 'Abiertos',
        'In Progress': 'En proceso',
        'Waiting': 'En espera',
        'Closed': 'Cerrados',
        'By category': 'Por categoría',
        'View tickets': 'Ver tickets',
        'Manage users': 'Gestionar usuarios',
        'Open tickets': 'Tickets abiertos',
        'In process': 'En proceso',
        'Waiting user': 'Esperando usuario',
        'Low': 'Baja',
        'Medium': 'Media',
        'High': 'Alta',
        'Critical': 'Crítica',
        'Network': 'Red',
        'Printers': 'Impresoras',
        'Software': 'Software',
        'Hardware': 'Hardware',
        'Abierto': 'Abierto',
        'En proceso': 'En proceso',
        'Esperando usuario': 'Esperando usuario',
        'Cerrado': 'Cerrado',
        'Baja': 'Baja',
        'Media': 'Media',
        'Alta': 'Alta',
        'Crítica': 'Crítica',
        'Red': 'Red',
        'Impresoras': 'Impresoras',
        'Corporate Support': 'Soporte Corporativo',
        'View Tickets': 'Ver Tickets',
        'Create Ticket': 'Crear Ticket',
        'Sign In': 'Entrar',
        'Key Features': 'Características Principales',
        'Everything you need for efficient support management': 'Todo lo que necesitas para una gestión eficiente del soporte',
        'Easy to Use': 'Fácil de Usar',
        'Intuitive interface designed for seamless ticket management and tracking': 'Interfaz intuitiva diseñada para una gestión y seguimiento perfecto de tickets',
        'SLA Tracking': 'Seguimiento de SLA',
        'Monitor response times and resolution SLAs for tickets with real-time alerts': 'Monitorea tiempos de respuesta y SLAs de resolución de tickets con alertas en tiempo real',
        'Collaborate': 'Colaborar',
        'Add comments and attachments to tickets for team collaboration': 'Agrega comentarios y adjuntos a los tickets para la colaboración del equipo',
        'Dashboard': 'Panel',
        'View analytics and KPIs across all tickets and support metrics': 'Ve analíticas y KPIs en todos los tickets y métricas de soporte',
        'Ready to get started?': '¿Listo para comenzar?',
        'Join the support system and manage tickets efficiently': 'Únete al sistema de soporte y gestiona tickets de manera eficiente',
        'Go to Tickets': 'Ir a Tickets',
        'Sign In Now': 'Entrar Ahora'
        , 'Please change the default admin password before continuing': 'Por seguridad, cambia la contraseña predeterminada de admin antes de continuar'
        , 'Password updated successfully': 'Contraseña actualizada correctamente'
        , 'New Password': 'Nueva contraseña'
        , 'Confirm Password': 'Confirmar contraseña'
        , 'Update Password': 'Actualizar contraseña'
        , 'Who We Are': 'Quiénes Somos'
        , 'Terms and Conditions': 'Términos y Condiciones'
        , 'Cookie Notice': 'Aviso de Cookies'
        , 'Cookie Preferences': 'Preferencias de Cookies'
        , 'We use essential cookies to keep the platform secure and functional. You can accept or reject optional cookies.': 'Usamos cookies esenciales para mantener la plataforma segura y funcional. Puede aceptar o rechazar las cookies opcionales.'
        , 'Reject': 'Rechazar'
        , 'Accept': 'Aceptar'
        , 'Please read these terms carefully before using the support system.': 'Por favor, lea estos términos cuidadosamente antes de usar el sistema de soporte.'
        , 'Acceptance of Terms': 'Aceptación de los Términos'
        , 'By accessing this platform, you agree to comply with these terms and all applicable policies.': 'Al acceder a esta plataforma, usted acepta cumplir estos términos y todas las políticas aplicables.'
        , 'Service Scope': 'Alcance del Servicio'
        , 'This system is intended for management of technical support tickets and related communication between users, technicians, and administrators.': 'Este sistema está destinado a la gestión de tickets de soporte técnico y la comunicación relacionada entre usuarios, técnicos y administradores.'
        , 'User Responsibilities': 'Responsabilidades del Usuario'
        , 'Provide truthful information in tickets and avoid abusive, illegal, or malicious content.': 'Proporcione información veraz en los tickets y evite contenido abusivo, ilegal o malicioso.'
        , 'Confidentiality and Data': 'Confidencialidad y Datos'
        , 'Information managed in tickets may include internal operational data and must be treated as confidential.': 'La información gestionada en los tickets puede incluir datos operativos internos y debe tratarse como confidencial.'
        , 'Password and Access Security': 'Seguridad de Contraseñas y Acceso'
        , 'Each user is responsible for safeguarding their credentials and promptly reporting unauthorized access.': 'Cada usuario es responsable de resguardar sus credenciales y reportar de inmediato cualquier acceso no autorizado.'
        , 'Availability and Changes': 'Disponibilidad y Cambios'
        , 'The service may be updated, suspended, or modified to improve security and performance.': 'El servicio puede actualizarse, suspenderse o modificarse para mejorar la seguridad y el rendimiento.'
        , 'Contact': 'Contacto'
        , 'For questions about these terms, contact the system administrator.': 'Para consultas sobre estos términos, contacte al administrador del sistema.'
        , 'Last updated': 'Última actualización'
        , 'We are a team focused on delivering agile, reliable corporate technical support with clear processes and people-centered service.': 'Somos un equipo enfocado en brindar soporte técnico corporativo, ágil y confiable, con procesos claros y atención centrada en las personas.'
        , 'Our Identity': 'Nuestra Identidad'
        , 'We combine technology, methodology, and service to keep your company operating without interruptions.': 'Combinamos tecnología, metodología y servicio para mantener la operación de tu empresa siempre en movimiento.'
        , 'Mission': 'Misión'
        , 'Resolve incidents and requests with speed, quality, and traceability, ensuring operational continuity for every business area.': 'Resolver incidentes y solicitudes con rapidez, calidad y trazabilidad, garantizando continuidad operativa para cada área de negocio.'
        , 'Vision': 'Visión'
        , 'Be a benchmark help desk in efficiency and user experience, driving decisions through metrics and continuous improvement.': 'Ser una mesa de ayuda referente en eficiencia y experiencia de usuario, impulsando decisiones con métricas y mejora continua.'
        , 'Values': 'Valores'
        , 'Commitment, transparency, collaboration, and customer focus in every interaction, from ticket creation to closure.': 'Compromiso, transparencia, colaboración y orientación al cliente en cada interacción, desde la apertura hasta el cierre del ticket.'
        , 'Ready to support you': 'Listos para apoyarte'
        , 'Our goal is for every team to work without interruptions, with professional and approachable technical support.': 'Nuestro objetivo es que cada equipo trabaje sin interrupciones, con soporte técnico profesional y cercano.'
        , 'Create ticket now': 'Crear ticket ahora'
        , 'Sign in to the system': 'Entrar al sistema'
        , 'Knowledge Base': 'Base de Conocimiento'
        , 'New Article': 'Nuevo Artículo'
        , 'Edit Article': 'Editar Artículo'
        , 'Save Article': 'Guardar Artículo'
        , 'Delete this article?': '¿Eliminar este artículo?'
        , 'Article created successfully': 'Artículo creado correctamente'
        , 'Article updated successfully': 'Artículo actualizado correctamente'
        , 'Article removed from knowledge base': 'Artículo eliminado de la base de conocimiento'
        , 'Title and content are required': 'El título y el contenido son obligatorios'
        , 'Use from KB': 'Usar de KB'
        , 'Search articles...': 'Buscar artículos...'
        , 'Type to search articles...': 'Escribe para buscar artículos...'
        , 'No articles found': 'No se encontraron artículos'
        , 'No articles found for': 'No se encontraron artículos para'
        , 'No articles yet. Create the first one!': 'Sin artículos aún. ¡Crea el primero!'
        , 'Insert': 'Insertar'
        , 'This text will be inserted into ticket comments when technicians use it.': 'Este texto se insertará en los comentarios del ticket cuando los técnicos lo usen.'
        , 'Executive Report': 'Reporte Ejecutivo'
        , 'IT Support — Executive Report': 'Soporte TI — Reporte Ejecutivo'
        , 'Generated on': 'Generado el'
        , 'Print / Export PDF': 'Imprimir / Exportar PDF'
        , 'Total Tickets': 'Total de Tickets'
        , 'SLA Compliance': 'Cumplimiento SLA'
        , 'Avg. Resolution Time': 'Tiempo Promedio de Resolución'
        , 'CSAT Average': 'Promedio CSAT'
        , 'Weekly Comparison': 'Comparación Semanal'
        , 'This week — Tickets created': 'Esta semana — Tickets creados'
        , 'Previous week — Tickets created': 'Semana anterior — Tickets creados'
        , 'This week — Tickets closed': 'Esta semana — Tickets cerrados'
        , 'Previous week — Tickets closed': 'Semana anterior — Tickets cerrados'
        , 'By Category': 'Por Categoría'
        , 'By Priority': 'Por Prioridad'
        , 'By Technician': 'Por Técnico'
        , 'No assignments yet': 'Sin asignaciones aún'
        , 'SLA Overdue Tickets': 'Tickets con SLA Vencido'
        , 'SLA Deadline': 'Límite SLA'
        , 'optional': 'opcional'
        , 'Updated': 'Actualizado'
        , 'Save to KB': 'Guardar en KB'
        , 'Published': 'Publicado'
        , 'Pending Approval': 'Pendiente de aprobacion'
        , 'Approve': 'Aprobar'
        , 'Article submitted for admin approval': 'Articulo enviado para aprobacion del administrador'
        , 'You can only edit your own pending KB proposals': 'Solo puedes editar tus propuestas KB pendientes'
        , 'Article approved and published': 'Articulo aprobado y publicado'
        , 'KB pending': 'KB pendientes'
        , 'Articles waiting for approval': 'Articulos esperando aprobacion'
        , 'Pending KB Proposals': 'Propuestas KB pendientes'
        , 'Actions': 'Acciones'
        , 'Ticket must be closed before creating a KB article': 'El ticket debe estar cerrado antes de crear un articulo de KB'
        , 'Capture this resolution in the Knowledge Base': 'Registra esta solucion en la Base de Conocimiento'
        , 'Create a reusable article from this closed ticket with one click.': 'Crea un articulo reutilizable desde este ticket cerrado con un solo clic.'
        , 'Create KB Article': 'Crear articulo de KB'
        , 'Comment added': 'Comentario agregado'
        , 'Welcome back, {username}!': '¡Bienvenido de nuevo, {username}!'
        , 'You have been logged out successfully': 'Has cerrado sesión correctamente'
        , 'User "{username}" created successfully with role: {role}': 'Usuario "{username}" creado correctamente con rol: {role}'
        , 'User "{username}" updated - New role: {role}': 'Usuario "{username}" actualizado - Nuevo rol: {role}'
        , 'Option "{value}" added to {type}': 'Opción "{value}" agregada a {type}'
        , 'Option "{value}" removed': 'Opción "{value}" eliminada'
        , 'Option updated to "{value}"': 'Opción actualizada a "{value}"'
        , 'Ticket #{id} updated successfully - Status: {status}': 'Ticket #{id} actualizado correctamente - Estado: {status}'
        , 'Active': 'Activo'
        , 'Inactive': 'Inactivo'
        , 'This account has been deactivated. Please contact an administrator.': 'Esta cuenta ha sido desactivada. Por favor contacta a un administrador.'
        , 'User "{username}" updated - Role: {role}, Status: {status}': 'Usuario "{username}" actualizado - Rol: {role}, Estado: {status}'
        , '-- Unassigned --': '-- Sin asignar --'
        , 'Details': 'Detalles'
        , 'SLA Information': 'Información SLA'
        , '(online)': '(en línea)'
        , 'Request password reset': 'Solicitar restablecimiento de contraseña'
        , 'Password reset request': 'Solicitud de restablecimiento de contraseña'
        , 'User requested password reset. Registered email: {email}': 'El usuario solicitó restablecimiento de contraseña. Correo registrado: {email}'
        , 'Password reset ticket created successfully': 'Ticket de restablecimiento de contraseña creado correctamente'
        , 'Requester email': 'Correo del solicitante'
        , 'This option is only for normal users': 'Esta opción es solo para usuarios normales'
        , 'Reset Password': 'Restablecer contraseña'
        , 'Password for user "{username}" was reset successfully': 'La contraseña del usuario "{username}" fue restablecida correctamente'
        , 'Registered email': 'Correo registrado'
        , 'ML System': 'Sistema ML'
        , 'ML Classification System': 'Sistema de Clasificación ML'
        , 'Intelligent Ticket Classification System': 'Sistema Inteligente de Clasificación de Tickets'
        , 'ML Model Status': 'Estado del Modelo ML'
        , 'Model is trained and ready': 'Modelo entrenado y listo'
        , 'Trained on:': 'Entrenado el:'
        , 'Number of technicians:': 'Número de técnicos:'
        , 'Text features:': 'Características de texto:'
        , 'Prediction accuracy:': 'Precisión de predicción:'
        , 'Retrain Model': 'Reentrenar modelo'
        , 'This will retrain the model with current data. Continue?': 'Esto reentrenará el modelo con los datos actuales. ¿Continuar?'
        , 'Model not trained yet': 'Modelo no entrenado aún'
        , 'You need at least 10 closed tickets to train the model.': 'Necesitas al menos 10 tickets cerrados para entrenar el modelo.'
        , 'Train Model Now': 'Entrenar modelo ahora'
        , 'How It Works': 'Cómo funciona'
        , 'Analyzes ticket content:': 'Analiza el contenido del ticket:'
        , 'The system reads the title and description using NLP (Natural Language Processing).': 'El sistema lee el título y descripción usando PLN (Procesamiento de Lenguaje Natural).'
        , 'Considers category and priority:': 'Considera categoría y prioridad:'
        , 'Uses the selected category and priority level.': 'Usa la categoría y nivel de prioridad seleccionados.'
        , 'Evaluates technician expertise:': 'Evalúa la experiencia del técnico:'
        , 'Reviews past performance, resolution time, and specialization.': 'Revisa rendimiento pasado, tiempo de resolución y especialización.'
        , 'Suggests the best technician:': 'Sugiere el mejor técnico:'
        , 'Recommends the most suitable technician with a confidence score.': 'Recomienda el técnico más adecuado con un puntaje de confianza.'
        , 'Auto-assigns high-confidence tickets:': 'Auto-asigna tickets de alta confianza:'
        , 'If confidence > 70%, automatically assigns the ticket.': 'Si la confianza > 70%, asigna automáticamente el ticket.'
        , 'Technician Performance Statistics': 'Estadísticas de Rendimiento de Técnicos'
        , 'Tickets Resolved': 'Tickets resueltos'
        , 'Avg. Resolution Time': 'Tiempo promedio de resolución'
        , 'Avg. Satisfaction': 'Satisfacción promedio'
        , 'Top Category': 'Categoría principal'
        , 'hours': 'horas'
        , 'No statistics available yet. Statistics are calculated when the model is trained.': 'No hay estadísticas disponibles aún. Se calculan cuando se entrena el modelo.'
        , 'Recent ML Predictions': 'Predicciones ML recientes'
        , 'ML Suggested': 'Sugerido por ML'
        , 'Confidence': 'Confianza'
        , 'Actually Assigned': 'Realmente asignado'
        , 'Auto-assigned by ML': 'Auto-asignado por ML'
        , 'Unassigned': 'Sin asignar'
        , 'Match': 'Coincide'
        , 'Different': 'Diferente'
        , 'Back to Dashboard': 'Volver al Dashboard'
        , 'ML model trained successfully! Accuracy: {accuracy:.1%}': 'Modelo ML entrenado exitosamente! Precisión: {accuracy:.1%}'
        , 'Error training model: {error}': 'Error al entrenar el modelo: {error}'
        , 'Machine Learning dependencies not installed': 'Las dependencias de Machine Learning no están instaladas'
        , 'ML dependencies not installed. Please run: pip install scikit-learn numpy': 'Las dependencias de ML no están instaladas. Por favor ejecuta: pip install scikit-learn numpy'
        , 'Machine Learning dependencies not available': 'Las dependencias de Machine Learning no están disponibles'
        , 'ML dependencies are not installed. Install them manually:': 'Las dependencias de ML no están instaladas. Instálalas manualmente:'
        , 'After installation, redeploy the application.': 'Después de la instalación, vuelve a desplegar la aplicación.'
        , 'ML System Not Available': 'Sistema ML no disponible'
        , 'Please install ML dependencies': 'Por favor instala las dependencias de ML'
        , 'An error occurred loading the ML system': 'Ocurrió un error al cargar el sistema ML'
        , 'Integrations': 'Integraciones'
        , 'Chat Integrations': 'Integraciones de Chat'
        , 'API Tokens': 'Tokens de API'
        , 'Active Integrations': 'Integraciones activas'
        , 'Platform': 'Plataforma'
        , 'Token name is required': 'El nombre del token es requerido'
        , 'API token created successfully. Save it now, it won\'t be shown again: {token}': 'Token API creado exitosamente. Guárdalo ahora, no se mostrará de nuevo: {token}'
        , 'API token revoked': 'Token API revocado'
        , 'Platform and name are required': 'Plataforma y nombre son requeridos'
        , 'Integration created successfully': 'Integración creada exitosamente'
        , 'activated': 'activada'
        , 'deactivated': 'desactivada'
        , 'Integration {status}': 'Integración {status}'
        , 'Integration deleted': 'Integración eliminada'
        , 'Users Management': 'Gestión de Usuarios'
        , 'Ticket Options': 'Opciones de Ticket'
        , 'ML System': 'Sistema de ML'
        , 'AI System': 'Sistema de IA'
        , 'Settings Hub': 'Centro de Configuración'
        , 'Token Name': 'Nombre del token'
        , 'Created': 'Creado'
        , 'Last Used': 'Último uso'
        , 'Actions': 'Acciones'
        , 'Revoke': 'Revocar'
        , 'Revoked': 'Revocado'
        , 'Never': 'Nunca'
        , 'Create New Token': 'Crear nuevo token'
        , 'Create': 'Crear'
        , 'Webhook URL': 'URL del webhook'
        , 'Verification Token': 'Token de verificación'
        , 'Create New Integration': 'Crear nueva integración'
        , 'Toggle': 'Alternar'
        , 'Delete': 'Eliminar'
        , 'Optional': 'Opcional'
        , 'For Slack slash commands': 'Para comandos slash de Slack'
        , 'Manage API tokens and integrations with Slack, Teams, and other platforms': 'Gestiona tokens API e integraciones con Slack, Teams y otras plataformas'
        , 'Setup Instructions': 'Instrucciones de configuración'
        , 'AI System': 'Sistema de IA'
        , 'Sentiment Analysis': 'Análisis de sentimiento'
        , 'Auto-Response Chatbot': 'Chatbot de respuesta automática'
        , 'Sentiment': 'Sentimiento'
        , 'Very Negative': 'Muy negativo'
        , 'Negative': 'Negativo'
        , 'Neutral': 'Neutral'
        , 'Positive': 'Positivo'
        , 'Very Positive': 'Muy positivo'
        , 'Urgency': 'Urgencia'
        , 'High': 'Alta'
        , 'Medium': 'Media'
        , 'Low': 'Baja'
        , 'AI Response': 'Respuesta IA'
        , 'Provided by AI': 'Proporcionada por IA'
        , 'Mark as helpful': 'Marcar como útil'
        , 'This was helpful': 'Esto fue útil'
        , 'I need more help': 'Necesito más ayuda'
        , 'Enable AI': 'Habilitar IA'
        , 'Disable AI': 'Deshabilitar IA'
        , 'AI System Settings': 'Configuración del sistema de IA'
        , 'Enable sentiment analysis': 'Habilitar análisis de sentimiento'
        , 'Enable auto-response chatbot': 'Habilitar chatbot de respuesta automática'
        , 'Auto-response confidence threshold': 'Umbral de confianza de respuesta automática'
        , 'Minimum confidence (0-1) to send automatic response': 'Confianza mínima (0-1) para enviar respuesta automática'
        , 'Detected sentiment: {sentiment}': 'Sentimiento detectado: {sentiment}'
        , 'Urgency level: {urgency}': 'Nivel de urgencia: {urgency}'
        , 'System Settings': 'Configuración del Sistema'
        , 'Manage all system configurations in one place': 'Gestiona todas las configuraciones del sistema en un solo lugar'
        , 'Create, edit, and manage system users and their roles': 'Crea, edita y gestiona usuarios del sistema y sus roles'
        , 'Active': 'Activo'
        , 'Inactive': 'Inactivo'
        , 'No users found. Create the first user to get started.': 'No hay usuarios. Crea el primer usuario para comenzar.'
        , 'Configure categories and priority levels for tickets': 'Configura categorías y niveles de prioridad para los tickets'
        , 'Add New Option': 'Agregar nueva opción'
        , 'You need at least 10 closed tickets to train the model.': 'Necesitas al menos 10 tickets cerrados para entrenar el modelo.'
        , 'Unknown': 'Desconocido'
        , 'ML System Not Available': 'Sistema ML no disponible'
        , 'Please install ML dependencies': 'Por favor instala las dependencias de ML'
        , 'An error occurred loading the ML system': 'Ocurrió un error al cargar el sistema ML'
        , 'Considers category and priority:': 'Considera la categoría y prioridad:'
        , 'Uses the selected category and priority level.': 'Usa la categoría y nivel de prioridad seleccionados.'
        , 'Evaluates technician expertise:': 'Evalúa la experiencia del técnico:'
        , 'Reviews past performance, resolution time, and specialization.': 'Revisa el desempeño pasado, tiempo de resolución y especialización.'
        , 'Suggests the best technician:': 'Sugiere el mejor técnico:'
        , 'Recommends the most suitable technician with a confidence score.': 'Recomienda el técnico más adecuado con una puntuación de confianza.'
        , 'Auto-assigns high-confidence tickets:': 'Auto-asigna tickets de alta confianza:'
        , 'If confidence > 70%, automatically assigns the ticket.': 'Si la confianza > 70%, asigna automáticamente el ticket.'
        , 'Technician Performance Statistics': 'Estadísticas de desempeño del técnico'
        , 'Avg. Resolution Time': 'Tiempo promedio de resolución'
        , 'Avg. Satisfaction': 'Satisfacción promedio'
        , 'Top Category': 'Categoría principal'
        , 'hours': 'horas'
        , 'No statistics available yet. Statistics are calculated when the model is trained.': 'No hay estadísticas disponibles aún. Las estadísticas se calculan cuando se entrena el modelo.'
        , 'Automatically detects customer sentiment and urgency level': 'Detecta automáticamente el sentimiento del cliente y el nivel de urgencia'
        , 'Provides automatic responses to common questions and issues': 'Proporciona respuestas automáticas a preguntas y problemas comunes'
        , 'Customer is very angry or frustrated': 'El cliente está muy enojado o frustrado'
        , 'Customer is frustrated': 'El cliente está frustrado'
        , 'Customer is neutral or factual': 'El cliente es neutral o factual'
        , 'Customer is satisfied or friendly': 'El cliente está satisfecho o es amigable'
        , 'Detection Categories:': 'Categorías de detección:'
        , 'Supported Categories:': 'Categorías soportadas:'
        , 'Benefits:': 'Beneficios:'
        , 'Instant answers to common problems': 'Respuestas instantáneas a problemas comunes'
        , 'Reduces ticket queue by handling FAQs': 'Reduce la cola de tickets manejando preguntas frecuentes'
        , 'Improves customer satisfaction': 'Mejora la satisfacción del cliente'
        , 'Frees up technicians for complex issues': 'Libera a los técnicos para problemas complejos'
        , 'Responds automatically to common questions from our knowledge base.': 'Responde automáticamente a preguntas comunes de nuestra base de conocimientos.'
        , 'Analyzes ticket content to detect customer sentiment and urgency levels.': 'Analiza el contenido del ticket para detectar el sentimiento del cliente y los niveles de urgencia.'
        , 'API tokens allow external applications to create tickets programmatically.': 'Los tokens API permiten que aplicaciones externas creen tickets programáticamente.'
        , 'Configure webhooks for Slack, Microsoft Teams, and other platforms.': 'Configura webhooks para Slack, Microsoft Teams y otras plataformas.'
        , 'No API tokens yet. Create one to get started.': 'Sin tokens API aún. Crea uno para comenzar.'
        , 'Example: Slack Integration, Teams Bot, etc.': 'Ejemplo: Integración de Slack, Teams Bot, etc.'
        , 'No integrations configured yet.': 'Sin integraciones configuradas aún.'
        , 'Save Settings': 'Guardar configuración'
        , 'Analyzes the title and description using NLP (Natural Language Processing).': 'Analiza el título y la descripción usando PNL (Procesamiento de Lenguaje Natural).'
        , 'Other': 'Otro'
        , 'Integration name': 'Nombre de la integración'
        , 'Manage all system configurations and settings in one place': 'Gestiona todas las configuraciones y ajustes del sistema en un solo lugar'
        , 'My Tickets': 'Mis Tickets'
        , 'Change Password': 'Cambiar Contraseña'
        , 'Feature coming soon': 'Función próximamente'
        , 'Chat Monitoring': 'Monitoreo de Chats'
        , 'Direct chat': 'Chat directo'
        , 'Conversation between requester and assigned technician': 'Conversación entre solicitante y técnico asignado'
        , 'No messages yet': 'Sin mensajes aún'
        , 'Client': 'Cliente'
        , 'Technician': 'Técnico'
        , 'Admin': 'Administrador'
        , 'Active': 'Activo'
        , 'Inactive': 'Inactivo'
        , 'Last Hour': 'Última Hora'
        , 'With Messages': 'Con Mensajes'
        , 'Most Recent': 'Más reciente'
        , 'Most Messages': 'Más mensajes'
        , 'All Chats': 'Todos los chats'
        , 'All Statuses': 'Todos los estados'
        , 'Filter by Status': 'Filtrar por estado'
        , 'Filter by Activity': 'Filtrar por actividad'
        , 'Sort By': 'Ordenar por'
        , 'message(s)': 'mensaje(s)'
        , 'Last activity: ': 'Última actividad: '
        , 'Participants': 'Participantes'
        , 'Tech': 'Técnico'
        , 'Unassigned': 'Sin asignar'
        , 'View Chat': 'Ver Chat'
        , 'Online Users': 'Usuarios en línea'
        , 'user(s) currently online': 'usuario(s) en línea actualmente'
        , 'user currently online': 'usuario en línea actualmente'
        , 'Joined': 'Conectado'
        , 'Back to Dashboard': 'Volver al Dashboard'
        , 'Administrators': 'Administradores'
        , 'Technicians': 'Técnicos'
        , 'Users': 'Usuarios'
        , 'Total Online': 'Total en Línea'
        , 'No users online': 'Sin usuarios en línea'
        , 'Users will appear here when they connect to the system': 'Los usuarios aparecerán aquí cuando se conecten al sistema'
        , 'Current Password': 'Contraseña actual'
        , 'Current password is incorrect': 'La contraseña actual es incorrecta'
        , 'New password must be different from current password': 'La nueva contraseña debe ser diferente de la actual'
        , 'Password changed successfully': 'Contraseña cambiada exitosamente'
        , 'Update your account password': 'Actualiza la contraseña de tu cuenta'
        , 'Cancel': 'Cancelar'
        , 'Password Security Tips': 'Consejos de seguridad para contraseñas'
        , 'Use at least 8 characters': 'Usa al menos 8 caracteres'
        , 'Include numbers, letters and symbols': 'Incluye números, letras y símbolos'
        , 'Avoid common words or patterns': 'Evita palabras o patrones comunes'
        , 'Do not reuse recent passwords': 'No reutilices contraseñas recientes'
        , 'Minimum 8 characters': 'Mínimo 8 caracteres'
        , 'Error resetting password. Please try again.': 'Error al restablecer la contraseña. Por favor intenta nuevamente.'
        , 'Password does not meet security requirements: ': 'La contraseña no cumple los requisitos de seguridad: '
        , 'This password was recently used. Please choose a different one.': 'Esta contraseña fue usada recientemente. Por favor elige una diferente.'
    },
    'en': {
        'Abierto': 'Open',
        'En proceso': 'In progress',
        'Esperando usuario': 'Waiting user',
        'Cerrado': 'Closed',
        'Baja': 'Low',
        'Media': 'Medium',
        'Alta': 'High',
        'Crítica': 'Critical',
        'Red': 'Network',
        'Impresoras': 'Printers',
        'Usuario o contraseña inválidos': 'Invalid username or password',
        'Ticket creado correctamente': 'Ticket created successfully',
        'No tienes acceso a este ticket': 'You do not have access to this ticket',
        'Ticket actualizado': 'Ticket updated',
        'Se requiere acceso de administrador': 'Administrator access required',
        'Se requiere acceso de técnico o administrador': 'Technician or admin access required',
        'Usuario creado': 'User created',
        'Usuario actualizado': 'User updated',
        'Se requiere pandas para exportar a Excel': 'pandas required for excel export',
        'Opciones de ticket': 'Ticket options',
        'Gestionar opciones de ticket': 'Manage ticket options',
        'Categorías': 'Categories',
        'Prioridades': 'Priorities',
        'Eliminar': 'Delete',
        'Tipo': 'Type',
        'Valor': 'Value',
        'Agregar': 'Add',
        'No hay categorías configuradas': 'No categories configured',
        'No hay prioridades configuradas': 'No priorities configured',
        'Opción agregada': 'Option added',
        'Opción eliminada': 'Option removed',
        'Opción actualizada': 'Option updated',
        'La opción ya existe': 'Option already exists',
        'La opción ya existía y fue reactivada': 'Option already existed and was reactivated',
        'El valor es obligatorio': 'Value is required',
        'Actualizar': 'Update',
        'Acción': 'Action',
        'Vencimiento SLA': 'SLA Due',
        'Vencido': 'Overdue',
        'En tiempo': 'On time',
        'No se encontraron tickets': 'No tickets found',
        'Comentarios': 'Comments',
        'Reabierto': 'Reopened',
        'vez/veces': 'time(s)',
        'Adjuntos': 'Attachments',
        'Descargar': 'Download',
        'Sin adjuntos': 'No attachments',
        'Usuario': 'User',
        'Aún no hay comentarios': 'No comments yet',
        'Error': 'Error',
        'Ocurrió un error inesperado al procesar la solicitud': 'An unexpected error occurred',
        'Intenta nuevamente. Si el problema continúa, avisa al administrador.': 'Try again. If the problem persists, notify the administrator.',
        'Volver a tickets': 'Back to tickets',
        'SLA vencidos': 'Overdue SLA',
        'Promedio resolución (h)': 'Avg resolution (h)',
        'Tickets reabiertos': 'Reopened tickets',
        'Adjunto': 'Attachment',
        'Comentario': 'Comment',
        'Agregar comentario': 'Add comment',
        'Repetir contraseña': 'Repeat Password',
        'Actualizar ticket': 'Update Ticket',
        'Nuevo ticket creado': 'New ticket created',
        'Ver detalles': 'View Details',
        'Tu ticket fue actualizado': 'Your ticket was updated',
        'El ticket "{title}" fue creado por {username}.': 'Ticket "{title}" has been created by {username}.',
        'El estado de tu ticket "{title}" ahora es {status}.': 'Your ticket "{title}" status is now {status}.',
        'Bienvenido al sistema de soporte': 'Welcome to the support system',
        'Use la navegación para entrar o crear tickets.': 'Use navigation to sign in or create tickets.',
        'Ver Tickets': 'View Tickets',
        'Características Principales': 'Key Features',
        'Todo lo que necesitas para una gestión eficiente del soporte': 'Everything you need for efficient support management',
        'Fácil de Usar': 'Easy to Use',
        'Interfaz intuitiva diseñada para una gestión y seguimiento perfecto de tickets': 'Intuitive interface designed for seamless ticket management and tracking',
        'Seguimiento de SLA': 'SLA Tracking',
        'Monitorea tiempos de respuesta y SLAs de resolución de tickets con alertas en tiempo real': 'Monitor response times and resolution SLAs for tickets with real-time alerts',
        'Colaborar': 'Collaborate',
        'Agrega comentarios y adjuntos a los tickets para la colaboración del equipo': 'Add comments and attachments to tickets for team collaboration',
        'Ve analíticas y KPIs en todos los tickets y métricas de soporte': 'View analytics and KPIs across all tickets and support metrics',
        '¿Listo para comenzar?': 'Ready to get started?',
        'Únete al sistema de soporte y gestiona tickets de manera eficiente': 'Join the support system and manage tickets efficiently',
        'Ir a Tickets': 'Go to Tickets',
        'Entrar Ahora': 'Sign In Now',
        'Información Básica': 'Basic Information',
        'Opciones': 'Options',
        'Adjuntos': 'Attachments',
        'Formatos aceptados': 'Accepted formats',
        'Cancelar': 'Cancel',
        'Detalles': 'Details',
        'Información de SLA': 'SLA Information',
        'Vencimiento SLA': 'SLA Due',
        'Acciones Rápidas': 'Quick Actions',
        'Por categoría': 'By category',
        'Administrar usuarios': 'Manage users',
        'Administrar opciones de ticket': 'Manage ticket options',
        'Tu nombre': 'Your name',
        'Título del ticket': 'Ticket title',
        'Describe el problema en detalle': 'Describe the issue in detail',
        'Agregar un comentario...': 'Add a comment...',
        'AI System': 'AI System',
        'Sentiment Analysis': 'Sentiment Analysis',
        'Auto-Response Chatbot': 'Auto-Response Chatbot',
        'Sentiment': 'Sentiment',
        'Very Negative': 'Very Negative',
        'Negative': 'Negative',
        'Neutral': 'Neutral',
        'Positive': 'Positive',
        'Very Positive': 'Very Positive',
        'Urgency': 'Urgency',
        'High': 'High',
        'Medium': 'Medium',
        'Low': 'Low',
        'AI Response': 'AI Response',
        'Provided by AI': 'Provided by AI',
        'Mark as helpful': 'Mark as helpful',
        'This was helpful': 'This was helpful',
        'I need more help': 'I need more help',
        'Enable AI': 'Enable AI',
        'Disable AI': 'Disable AI',
        'AI System Settings': 'AI System Settings',
        'Enable sentiment analysis': 'Enable sentiment analysis',
        'Enable auto-response chatbot': 'Enable auto-response chatbot',
        'Auto-response confidence threshold': 'Auto-response confidence threshold',
        'Minimum confidence (0-1) to send automatic response': 'Minimum confidence (0-1) to send automatic response',
        'Detected sentiment: {sentiment}': 'Detected sentiment: {sentiment}',
        'Urgency level: {urgency}': 'Urgency level: {urgency}',
        'Configuración': 'Settings',
        'Gestión de Usuarios': 'Users Management',
        'Opciones de Ticket': 'Ticket Options',
        'Sistema de ML': 'ML System',
        'Sistema de IA': 'AI System',
        'Centro de Configuración': 'Settings Hub',
        'System Settings': 'System Settings',
        'Manage all system configurations in one place': 'Manage all system configurations in one place',
        'Create, edit, and manage system users and their roles': 'Create, edit, and manage system users and their roles',
        'Active': 'Active',
        'Inactive': 'Inactive',
        'No users found. Create the first user to get started.': 'No users found. Create the first user to get started.',
        'Configure categories and priority levels for tickets': 'Configure categories and priority levels for tickets',
        'Add New Option': 'Add New Option',
        'You need at least 10 closed tickets to train the model.': 'You need at least 10 closed tickets to train the model.',
        'Unknown': 'Unknown',
        'ML System Not Available': 'ML System Not Available',
        'Please install ML dependencies': 'Please install ML dependencies',
        'An error occurred loading the ML system': 'An error occurred loading the ML system',
        'Considers category and priority:': 'Considers category and priority:',
        'Uses the selected category and priority level.': 'Uses the selected category and priority level.',
        'Evaluates technician expertise:': 'Evaluates technician expertise:',
        'Reviews past performance, resolution time, and specialization.': 'Reviews past performance, resolution time, and specialization.',
        'Suggests the best technician:': 'Suggests the best technician:',
        'Recommends the most suitable technician with a confidence score.': 'Recommends the most suitable technician with a confidence score.',
        'Auto-assigns high-confidence tickets:': 'Auto-assigns high-confidence tickets:',
        'If confidence > 70%, automatically assigns the ticket.': 'If confidence > 70%, automatically assigns the ticket.',
        'Technician Performance Statistics': 'Technician Performance Statistics',
        'Avg. Resolution Time': 'Avg. Resolution Time',
        'Avg. Satisfaction': 'Avg. Satisfaction',
        'Top Category': 'Top Category',
        'hours': 'hours',
        'No statistics available yet. Statistics are calculated when the model is trained.': 'No statistics available yet. Statistics are calculated when the model is trained.',
        'Automatically detects customer sentiment and urgency level': 'Automatically detects customer sentiment and urgency level',
        'Provides automatic responses to common questions and issues': 'Provides automatic responses to common questions and issues',
        'Customer is very angry or frustrated': 'Customer is very angry or frustrated',
        'Customer is frustrated': 'Customer is frustrated',
        'Customer is neutral or factual': 'Customer is neutral or factual',
        'Customer is satisfied or friendly': 'Customer is satisfied or friendly',
        'Detection Categories:': 'Detection Categories:',
        'Supported Categories:': 'Supported Categories:',
        'Benefits:': 'Benefits:',
        'Instant answers to common problems': 'Instant answers to common problems',
        'Reduces ticket queue by handling FAQs': 'Reduces ticket queue by handling FAQs',
        'Improves customer satisfaction': 'Improves customer satisfaction',
        'Frees up technicians for complex issues': 'Frees up technicians for complex issues',
        'Responds automatically to common questions from our knowledge base.': 'Responds automatically to common questions from our knowledge base.',
        'Analyzes ticket content to detect customer sentiment and urgency levels.': 'Analyzes ticket content to detect customer sentiment and urgency levels.',
        'API tokens allow external applications to create tickets programmatically.': 'API tokens allow external applications to create tickets programmatically.',
        'Configure webhooks for Slack, Microsoft Teams, and other platforms.': 'Configure webhooks for Slack, Microsoft Teams, and other platforms.',
        'No API tokens yet. Create one to get started.': 'No API tokens yet. Create one to get started.',
        'Example: Slack Integration, Teams Bot, etc.': 'Example: Slack Integration, Teams Bot, etc.',
        'No integrations configured yet.': 'No integrations configured yet.',
        'Save Settings': 'Save Settings',
        'Analyzes the title and description using NLP (Natural Language Processing).': 'Analyzes the title and description using NLP (Natural Language Processing).',
        'Other': 'Other',
        'Integration name': 'Integration name',
        'Manage all system configurations and settings in one place': 'Manage all system configurations and settings in one place',
        'My Tickets': 'My Tickets',
        'Change Password': 'Change Password',
        'Feature coming soon': 'Feature coming soon',
    }
}


def translate(text: str, lang: str = 'en') -> str:
    return TRANSLATIONS.get(lang, {}).get(text, text)


def send_email(subject, recipients, body, html=None):
    # helper used by views; respect MAIL_SUPPRESS_SEND to avoid real SMTP during tests
    if current_app.config.get('MAIL_SUPPRESS_SEND'):
        current_app.logger.debug('send_email suppressed: %s -> %s', subject, recipients)
    else:
        msg = Message(subject, recipients=recipients)
        msg.body = body
        if html:
            msg.html = html
        mail.send(msg)

    # always attempt webhook notification if configured
    send_webhook(body)


def send_webhook(message: str):
    """Post a simple text message to configured chat webhook (Slack/Teams)."""
    url = current_app.config.get('CHAT_WEBHOOK_URL')
    if not url:
        return
    try:
        import requests
        # Slack/Teams both accept JSON payloads with a 'text' field
        requests.post(url, json={'text': message})
    except Exception as e:
        current_app.logger.error('webhook send failed: %s', e)


def _validate_secret_key(app):
    """Validate SECRET_KEY and enforce stricter rules in production."""
    secret_key = app.config.get('SECRET_KEY', '')
    secret_key_invalid = (
        not secret_key
        or secret_key == 'you-will-never-guess'
        or len(secret_key) < 12
    )
    if not secret_key_invalid:
        return

    app_logger = logging.getLogger(__name__)

    # Production must never run with a weak/missing secret.
    if os.environ.get('RENDER') == 'true':
        app_logger.critical('CRITICAL SECURITY: SECRET_KEY is weak or missing in production.')
        app_logger.critical('Set SECRET_KEY in Render Environment (minimum 12 chars).')
        raise RuntimeError('Missing or weak SECRET_KEY in production environment')

    # Development fallback for local convenience.
    app_logger.warning('SECRET_KEY is weak or missing in development. Generating temporary key.')
    app.config['SECRET_KEY'] = os.urandom(32).hex()
    print('\nWARNING: SECRET_KEY not set in environment. Set it in .env or Render settings:')
    print('   Minimum 12 characters, recommended 24+')
    print('   Example: export SECRET_KEY="$(python -c "import secrets; print(secrets.token_hex(6))")"')


def create_app(config_class=None):
    # Load environment variables from .env file
    load_dotenv()
    
    app = Flask(__name__)
    app.config.from_object(config_class or 'config.Config')

    _validate_secret_key(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)

    # Rate limiting storage: prefer Redis in production, fallback to memory for local/dev.
    rate_limit_storage = (
        os.environ.get('RATELIMIT_STORAGE_URI')
        or os.environ.get('REDIS_URL')
        or 'memory://'
    )
    app.config['RATELIMIT_STORAGE_URI'] = rate_limit_storage
    if rate_limit_storage == 'memory://' and os.environ.get('RENDER') == 'true':
        app.logger.warning('⚠️  Flask-Limiter using in-memory storage in production. Configure REDIS_URL to harden rate limits.')

    limiter.init_app(app)
    socketio.init_app(
        app, 
        cors_allowed_origins='*',  # Allow WebSocket connections from anywhere
        manage_session=True,  # Allow access to Flask session and current_user
        async_mode='eventlet',
        logger=True,
        engineio_logger=True,
        ping_timeout=60,
        ping_interval=25
    )
    
    # Configure Talisman with proper CSP for CDN resources
    csp_policy = {
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net"],
        'style-src': ["'self'", "'unsafe-inline'", "cdn.jsdelivr.net", "fonts.googleapis.com"],
        'font-src': ["'self'", "cdn.jsdelivr.net", "fonts.gstatic.com"],
        'img-src': ["'self'", "data:", "cdn.jsdelivr.net"],
        'connect-src': ["'self'", 'wss:', 'https:'],
    }
    # Configure Talisman - disable force_https to allow Render health checks
    # Render's proxy handles HTTPS termination
    talisman.init_app(
        app, 
        force_https=False,  # Render proxy handles HTTPS
        content_security_policy=csp_policy,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        strict_transport_security_preload=True
    )
    
    # CORS Configuration - Allow only your domain
    cors_config = {
        'origins': os.environ.get('CORS_ORIGINS', 'http://localhost:5000').split(','),
        'allow_headers': ['Content-Type', 'Authorization', 'X-Requested-With'],
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        'supports_credentials': True,
        'max_age': 3600
    }
    cors.init_app(app, resources={r'/api/*': cors_config})
    
    # Sentry Monitoring (if configured)
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,  # 10% of transactions
            environment=os.environ.get('FLASK_ENV', 'production')
        )
        current_app.logger.info('✓ Sentry monitoring initialized')

    # ensure loader registered (in case auth module import didn't run yet)
    @login.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.tickets import bp as tickets_bp
    app.register_blueprint(tickets_bp, url_prefix='/tickets')

    # admin blueprint for user management
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # API blueprint for external integrations
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    from app import routes, models  # noqa: F401

    # register main routes blueprint
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    # make current year available in templates for footer
    @app.context_processor
    def inject_current_year():
        from datetime import datetime
        lang = session.get('lang', 'en')

        def _translate(text):
            return translate(text, lang)

        return {
            'current_year': datetime.utcnow().year,
            '_': _translate,
            'current_lang': lang,
        }
    
    # Add custom Jinja2 filters
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Convert JSON string to Python dict"""
        if not value:
            return {}
        try:
            import json
            return json.loads(value)
        except:
            return {}

    @app.before_request
    def update_user_activity_and_enforce_password():
        if current_user.is_authenticated:
            # Update last_activity timestamp and in-memory online presence.
            from datetime import datetime, timedelta
            current_user.last_activity = datetime.utcnow()

            # Fallback presence tracking in case Socket.IO is unavailable.
            existing = online_users.get(current_user.id, {})
            online_users[current_user.id] = {
                'username': current_user.username,
                'user_role': current_user.role,
                'joined_at': existing.get('joined_at', datetime.utcnow()),
                'last_seen': datetime.utcnow(),
            }

            # Cleanup stale users (no activity in last 90 seconds).
            stale_after = datetime.utcnow() - timedelta(seconds=90)
            stale_ids = [
                uid for uid, info in online_users.items()
                if info.get('last_seen', info.get('joined_at', datetime.utcnow())) < stale_after
            ]
            for uid in stale_ids:
                online_users.pop(uid, None)

            try:
                db.session.commit()
            except:
                db.session.rollback()
        
        if not current_user.is_authenticated:
            return None

        endpoint = request.endpoint or ''
        allowed_endpoints = {
            'auth.force_password_change',
            'auth.logout',
            'main.set_language',
            'static',
        }
        if endpoint in allowed_endpoints or endpoint.startswith('static'):
            return None

        from app.auth import must_change_default_admin_password
        if must_change_default_admin_password(current_user):
            return redirect(url_for('auth.force_password_change'))

        return None

    # app logging to file to diagnose production errors without crashing user flow
    log_dir = app.instance_path
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.ERROR)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException) and error.code != 500:
            return error
        app.logger.exception('Unhandled exception: %s', error)
        return render_template('errors/500.html'), 500

    # Bootstrap for first deployment (e.g. fresh Render instance):
    # create tables if missing and seed default admin user.
    with app.app_context():
        try:
            from app.models import User
            db.create_all()

            # Add is_active column if it doesn't exist (migration support)
            inspector = db.inspect(db.engine)
            user_columns = [col['name'] for col in inspector.get_columns('user')]
            if 'is_active' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE'))
                    conn.commit()
                app.logger.warning('Added is_active column to user table')

            if 'last_activity' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
                    conn.commit()
                app.logger.warning('Added last_activity column to user table')

            # Add 2FA and security columns to user table
            if 'totp_secret' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN totp_secret VARCHAR(32)'))
                    conn.commit()
                app.logger.warning('Added totp_secret column to user table')

            if 'totp_enabled' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE'))
                    conn.commit()
                app.logger.warning('Added totp_enabled column to user table')

            if 'totp_backup_codes' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN totp_backup_codes TEXT'))
                    conn.commit()
                app.logger.warning('Added totp_backup_codes column to user table')

            if 'password_changed_at' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN password_changed_at TIMESTAMP'))
                    conn.commit()
                app.logger.warning('Added password_changed_at column to user table')

            if 'failed_login_attempts' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN failed_login_attempts INTEGER DEFAULT 0'))
                    conn.commit()
                app.logger.warning('Added failed_login_attempts column to user table')

            if 'last_failed_login_at' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN last_failed_login_at TIMESTAMP'))
                    conn.commit()
                app.logger.warning('Added last_failed_login_at column to user table')

            if 'locked_until' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN locked_until TIMESTAMP'))
                    conn.commit()
                app.logger.warning('Added locked_until column to user table')

            # Add ML-related columns to ticket table
            ticket_columns = [col['name'] for col in inspector.get_columns('ticket')]
            
            if 'resolution_time_minutes' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN resolution_time_minutes INTEGER'))
                    conn.commit()
                app.logger.warning('Added resolution_time_minutes column to ticket table')
            
            if 'satisfaction_rating' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN satisfaction_rating INTEGER'))
                    conn.commit()
                app.logger.warning('Added satisfaction_rating column to ticket table')
            
            if 'ml_suggested_technician_id' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN ml_suggested_technician_id INTEGER REFERENCES "user"(id)'))
                    conn.commit()
                app.logger.warning('Added ml_suggested_technician_id column to ticket table')
            
            if 'ml_confidence_score' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN ml_confidence_score REAL'))
                    conn.commit()
                app.logger.warning('Added ml_confidence_score column to ticket table')
            
            if 'auto_assigned' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN auto_assigned BOOLEAN DEFAULT FALSE'))
                    conn.commit()
                app.logger.warning('Added auto_assigned column to ticket table')
            
            # Add AI sentiment analysis columns
            if 'sentiment_label' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN sentiment_label VARCHAR(20)'))
                    conn.commit()
                app.logger.warning('Added sentiment_label column to ticket table')
            
            if 'sentiment_score' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN sentiment_score REAL'))
                    conn.commit()
                app.logger.warning('Added sentiment_score column to ticket table')
            
            if 'urgency_level' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN urgency_level VARCHAR(20)'))
                    conn.commit()
                app.logger.warning('Added urgency_level column to ticket table')
            
            # Add AI chatbot fields
            if 'ai_response' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN ai_response TEXT'))
                    conn.commit()
                app.logger.warning('Added ai_response column to ticket table')
            
            if 'ai_response_id' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN ai_response_id INTEGER'))
                    conn.commit()
                app.logger.warning('Added ai_response_id column to ticket table')
            
            if 'ai_response_confidence' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN ai_response_confidence REAL'))
                    conn.commit()
                app.logger.warning('Added ai_response_confidence column to ticket table')
            
            if 'ai_response_accepted' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN ai_response_accepted BOOLEAN'))
                    conn.commit()
                app.logger.warning('Added ai_response_accepted column to ticket table')

            # Create technician_stats table if it doesn't exist
            if not inspector.has_table('technician_stats'):
                from app.models import TechnicianStats
                TechnicianStats.__table__.create(db.engine)
                app.logger.warning('Created technician_stats table')
            
            # Create api_token table if it doesn't exist
            if not inspector.has_table('api_token'):
                from app.models import ApiToken
                ApiToken.__table__.create(db.engine)
                app.logger.warning('Created api_token table')
            
            # Create integration table if it doesn't exist
            if not inspector.has_table('integration'):
                from app.models import Integration
                Integration.__table__.create(db.engine)
                app.logger.warning('Created integration table')

            # Create audit_log table if it doesn't exist
            if not inspector.has_table('audit_log'):
                from app.models import AuditLog
                AuditLog.__table__.create(db.engine)
                app.logger.warning('Created audit_log table')

            # Create password_history table if it doesn't exist
            if not inspector.has_table('password_history'):
                from app.models import PasswordHistory
                PasswordHistory.__table__.create(db.engine)
                app.logger.warning('Created password_history table')

            default_admin_username = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
            default_admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
            default_admin_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@eie-puj.com')

            existing_admin = User.query.filter_by(username=default_admin_username).first()
            if existing_admin is None:
                admin_user = User(
                    username=default_admin_username,
                    email=default_admin_email,
                    role='admin'
                )
                admin_user.set_password(default_admin_password)
                db.session.add(admin_user)
                db.session.commit()
                app.logger.warning('Default admin user created for initial setup: %s', default_admin_username)
        except IntegrityError:
            db.session.rollback()
        except SQLAlchemyError as e:
            db.session.rollback()
            app.logger.error('Database bootstrap failed: %s', e)

    # Register ML commands
    from app.ml_commands import register_ml_commands
    register_ml_commands(app)

    return app


# Compatibility entrypoint for platforms configured with: gunicorn app:app
config_name = 'config.ProductionConfig' if os.environ.get('FLASK_ENV') == 'production' else 'config.Config'
app = create_app(config_name)
