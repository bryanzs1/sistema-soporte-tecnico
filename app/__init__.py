from flask import Flask, current_app, session, render_template, request, redirect, url_for
from flask_wtf.csrf import generate_csrf
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_cors import CORS
from flask_socketio import SocketIO
from datetime import datetime, timedelta, timezone

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from dotenv import load_dotenv
import os
import sys
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


def utcnow():
    """Return naive UTC datetime compatible with existing DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _rate_limit_key():
    """Use real client IP behind reverse proxies (Render) before fallback."""
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return get_remote_address()


limiter = Limiter(key_func=_rate_limit_key)
talisman = Talisman()
cors = CORS()
socketio = SocketIO()

# Global registry of online users: {user_id: {'username': str, 'joined_at': datetime}}
online_users = {}


TRANSLATIONS = {
    'es': {
        'Support': 'Soporte',
        'Tickets': 'Tickets',
        'Dashboard': 'Panel',
        'Admin': 'Admin',
        'Settings': 'Configuración',
        'Companies': 'Empresas',
        'Company': 'Empresa',
        'New company': 'Nueva empresa',
        'Edit company': 'Editar empresa',
        'Company name': 'Nombre de la empresa',
        'Register and manage the companies available in the platform.': 'Registrar y administrar las empresas disponibles en la plataforma.',
        'Register and manage companies': 'Registrar y administrar empresas',
        'No companies registered yet.': 'No hay empresas registradas todavía.',
        'Actions': 'Acciones',
        'Edit': 'Editar',
        'Save': 'Guardar',
        'Cancel': 'Cancelar',
        'Logout': 'Cerrar sesión',
        'Are you sure you want to log out?': '¿Seguro que deseas cerrar sesión?',
        'You have unsaved changes. If you leave this page, your information will be lost.': 'Tienes cambios sin guardar. Si sales de esta página, la información se perderá.',
        'Login': 'Iniciar sesión',
        'Forgot your password?': '¿Olvidaste tu contraseña?',
        'Reset your password': 'Restablece tu contraseña',
        'Enter your account email and we will send you a reset link.': 'Ingresa el correo de tu cuenta y te enviaremos un enlace para restablecerla.',
        'Request reset link': 'Solicitar enlace de restablecimiento',
        'Back to login': 'Volver al inicio de sesión',
        'Password reset link': 'Enlace para restablecer contraseña',
        'Open this link to reset your password: {url}': 'Abre este enlace para restablecer tu contraseña: {url}',
        'If the email exists in our system, you will receive password reset instructions shortly.': 'Si el correo existe en nuestro sistema, recibirás instrucciones de restablecimiento en breve.',
        'Invalid or expired password reset link. Request a new one.': 'El enlace de restablecimiento es inválido o expiró. Solicita uno nuevo.',
        'Set a new password': 'Define una nueva contraseña',
        'Your password has been reset successfully. Please sign in.': 'Tu contraseña fue restablecida correctamente. Inicia sesión.',
        'Language': 'Idioma',
        'English': 'Inglés',
        'Spanish': 'Español',
        'Support Assistant': 'Asistente de soporte',
        'How can I help you today?': '¿Cómo puedo ayudarte hoy?',
        'Pregúntame sobre contraseña, VPN, impresoras, correo o incidencias técnicas generales.': 'Ask me about password, VPN, printers, email, or general technical issues.',
        'Abrir asistente de soporte': 'Open support assistant',
        'Cerrar asistente': 'Close assistant',
        'Describe tu problema...': 'Describe tu problema...',
        'Enviar': 'Send',
        'El asistente está pensando...': 'Assistant is thinking...',
        'Categoría sugerida': 'Suggested category',
        'Crear ticket con este contexto': 'Create ticket with this context',
        'Necesito ayuda para restablecer mi contraseña': 'I need help resetting my password',
        'No puedo conectarme a la VPN': 'I cannot connect to the VPN',
        'Mi impresora no funciona': 'My printer is not working',
        'No estoy recibiendo correos': 'I am not receiving emails',
        'Restablecer contraseña': 'Password reset',
        'Acceso VPN': 'VPN access',
        'Problema de impresora': 'Printer issue',
        'Problema de correo': 'Email issue',
        'Describe un poco mejor tu problema para que pueda ayudarte.': 'Please describe your issue in a bit more detail so I can help you better.',
        'Aún no encontré una respuesta precisa, pero puedo ayudarte a crear un ticket con la información que ya escribiste.': "I couldn't find a precise answer yet, but I can help you create a ticket with the information you've already typed.",
        'No pude procesar tu solicitud en este momento. Crea un ticket y un técnico te ayudará.': 'I could not process your request right now. Please create a ticket and a technician will help you.',
        'Solicitud de soporte': 'Support request',
        '¿Seguro que deseas cerrar sesión?': 'Are you sure you want to log out?',
        'Tienes cambios sin guardar. Si sales de esta página, la información se perderá.': 'You have unsaved changes. If you leave this page, your information will be lost.',
        '¿Olvidaste tu contraseña?': 'Forgot your password?',
        'Restablece tu contraseña': 'Reset your password',
        'Ingresa el correo de tu cuenta y te enviaremos un enlace para restablecerla.': 'Enter your account email and we will send you a reset link.',
        'Solicitar enlace de restablecimiento': 'Request reset link',
        'Volver al inicio de sesión': 'Back to login',
        'Enlace para restablecer contraseña': 'Password reset link',
        'Abre este enlace para restablecer tu contraseña: {url}': 'Open this link to reset your password: {url}',
        'Si el correo existe en nuestro sistema, recibirás instrucciones de restablecimiento en breve.': 'If the email exists in our system, you will receive password reset instructions shortly.',
        'El enlace de restablecimiento es inválido o expiró. Solicita uno nuevo.': 'Invalid or expired password reset link. Request a new one.',
        'Define una nueva contraseña': 'Set a new password',
        'Tu contraseña fue restablecida correctamente. Inicia sesión.': 'Your password has been reset successfully. Please sign in.',
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
        'Restaurar opciones recomendadas': 'Restore recommended options',
        'Opciones recomendadas restauradas: {count}': 'Recommended options restored: {count}',
        'Las opciones de ticket ya están actualizadas': 'Ticket options are already up to date',
        'Gestionar opciones de ticket': 'Manage ticket options',
        'Categorías': 'Categories',
        'Prioridades': 'Priorities',
        'Eliminar': 'Delete',
        'Eliminar usuario': 'Delete User',
        'Eliminar permanentemente': 'Delete Permanently',
        '¿Estás seguro de que deseas eliminar permanentemente al usuario': 'Are you sure you want to permanently delete user',
        'Esta acción no se puede deshacer.': 'This action cannot be undone.',
        'Los registros existentes se reasignarán al administrador': 'Existing records will be reassigned to administrator',
        'Esta acción no se puede deshacer. Los usuarios con registros existentes deben desactivarse en su lugar.': 'This action cannot be undone. Users with existing records must be deactivated instead.',
        'No puedes eliminar tu propia cuenta.': 'You cannot delete your own account.',
        'No se puede eliminar la última cuenta de administrador.': 'Cannot delete the last administrator account.',
        'El usuario "{username}" tiene registros asociados y no puede eliminarse. Desactiva la cuenta en su lugar.': 'User "{username}" has associated records and cannot be deleted. Deactivate the account instead.',
        'El usuario "{username}" ha sido eliminado permanentemente.': 'User "{username}" has been permanently deleted.',
        'Error al eliminar usuario. Por favor intenta de nuevo.': 'Error deleting user. Please try again.',
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
        'Tomar ticket': 'Take ticket',
        'Liberar ticket': 'Release ticket',
        '¿Necesitas devolver este ticket a la cola?': 'Need to return this ticket to the queue?',
        'Al liberarlo se quitará el técnico asignado y el ticket volverá a abierto.': 'Releasing it will remove the assigned technician and set the ticket back to open.',
        'Ticket liberado por {username} y devuelto a la cola sin asignar': 'Ticket released by {username} and returned to the unassigned queue',
        'El ticket #{id} fue liberado correctamente': 'Ticket #{id} was released successfully',
        'Este ticket ya está sin asignar': 'This ticket is already unassigned',
        'Solo puedes liberar tickets asignados a ti': 'You can only release tickets assigned to you',
        'Solo los administradores pueden asignar o reasignar técnicos': 'Only administrators can assign or reassign technicians',
        'Política de asignación de tickets': 'Ticket assignment policy',
        'Permitir que los técnicos asignen o reasignen tickets': 'Allow technicians to assign or reassign tickets',
        'Reasignación por técnicos habilitada': 'Technician reassignment enabled',
        'Guardar política': 'Save policy',
        'Los técnicos ahora pueden reasignar tickets': 'Technicians can now reassign tickets',
        'Solo los administradores pueden reasignar tickets': 'Only administrators can reassign tickets',
        'Los tickets cerrados no se pueden liberar': 'Closed tickets cannot be released',
        'Este ticket está esperando un técnico': 'This ticket is waiting for a technician',
        'Puedes tomar este ticket y empezar a trabajarlo de inmediato.': 'You can take ownership of this ticket and start working on it immediately.',
        'Ticket tomado por el técnico {username}': 'Ticket taken by technician {username}',
        'Has tomado el ticket #{id} correctamente': 'You have taken ticket #{id} successfully',
        'Este ticket ya está asignado a otro técnico': 'This ticket is already assigned to another technician',
        'Este ticket ya está asignado a ti': 'This ticket is already assigned to you',
        'Los tickets cerrados no se pueden tomar': 'Closed tickets cannot be taken',
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
        'Asistente de soporte con IA': 'AI Support Assistant',
        'Asistente flotante con IA para resolver incidencias técnicas y guiar a los usuarios con pasos accionables.': 'Floating assistant with AI to help resolve technical issues and guide users with actionable steps.',
        'Creación guiada de tickets': 'Guided Ticket Creation',
        'Convierte conversaciones en tickets prellenados con contexto, sugerencias de categoría y triaje más rápido.': 'Turn conversations into prefilled tickets with context, category suggestions, and faster triage.',
        'Clasificación automática': 'Automatic Classification',
        'Detecta categorías como VPN, impresoras, correo, cuentas y software para enrutar solicitudes correctamente.': 'Detects categories like VPN, printers, email, accounts, and software to route requests correctly.',
        'Panel operativo': 'Operational Dashboard',
        'Monitorea SLAs, estados de tickets y desempeño del soporte con visibilidad operativa en tiempo real.': 'Track SLAs, ticket states, and support performance with real-time operational visibility.',
        '¿Listo para comenzar?': 'Ready to get started?',
        'Únete al sistema de soporte y gestiona tickets de manera eficiente': 'Join the support system and manage tickets efficiently',
        'Ir a Tickets': 'Go to Tickets',
        'Entrar Ahora': 'Sign In Now',
        'Personalizar tabla': 'Customize table',
        'Restablecer diseño de tabla': 'Reset table layout',
        'Arrastra y suelta los encabezados para reordenar. Activa o desactiva columnas abajo.': 'Drag and drop column headers to reorder. Enable or disable columns below.',
        'Información Básica': 'Basic Information',
        'Opciones': 'Options',
        'Línea de tiempo': 'Timeline',
        'Primera respuesta': 'First response',
        'El equipo de soporte comenzó a trabajar en el ticket': 'Support team started working on the ticket',
        'Resuelto': 'Resolved',
        'Ticket marcado como cerrado': 'Ticket marked as closed',
        'Ticket creado por {name}': 'Ticket created by {name}',
        'Aún no hay eventos en la línea de tiempo': 'No timeline data available yet',
        '¿Necesitas más ayuda?': 'Need more help?',
        'Puedes reabrir este ticket con un motivo para que el equipo continúe el soporte.': 'You can reopen this ticket with a reason so the team can continue support.',
        'Reabrir ticket': 'Reopen ticket',
        'Solo se pueden reabrir tickets cerrados': 'Only closed tickets can be reopened',
        'Por favor ingresa un motivo breve para reabrir el ticket': 'Please provide a short reason to reopen the ticket',
        'Motivo de reapertura: {reason}': 'Reopen reason: {reason}',
        'Ticket reabierto correctamente': 'Ticket reopened successfully',
        'Notificación de ticket reabierto': 'Ticket reopened notification',
        'El ticket #{id} fue reabierto por {user}. Motivo: {reason}': 'Ticket #{id} was reopened by {user}. Reason: {reason}',
        'Reapertura disponible hasta': 'Reopen available until',
        'Período de reapertura vencido': 'Reopen period expired',
        'Ventana de reapertura vencida. Los tickets cerrados solo pueden reabrirse dentro de 7 días.': 'Reopen window expired. Closed tickets can only be reopened within 7 days.',
        'Escribe CERRAR para confirmar el cierre de este ticket': 'Type CERRAR to confirm closing this ticket',
        'La acción de cierre del ticket fue cancelada': 'Ticket close action was cancelled',
        '¿Revocar este token API?': 'Revoke this API token?',
        'Escribe REVOCAR para confirmar la revocación del token': 'Type REVOCAR to confirm token revocation',
        'Este ticket fue reabierto {count} vez/veces': 'This ticket was reopened {count} time(s)',
        'Respuesta rápida: Acuse recibido': 'Quick reply: Acknowledged',
        'Respuesta rápida: Solicitar evidencia': 'Quick reply: Ask for evidence',
        'Respuesta rápida: Resolución': 'Quick reply: Resolution',
        'Hola, estamos revisando tu caso y te actualizaremos en breve.': 'Hello, we are reviewing your case and will update you shortly.',
        'Por favor comparte una captura o el mensaje de error exacto para continuar.': 'Please share a screenshot or exact error message so we can continue.',
        'Incidente resuelto. Por favor confirma si todo funciona correctamente de tu lado.': 'Issue resolved. Please confirm if everything is working correctly on your side.',
        'Soluciones sugeridas desde la Base de Conocimiento': 'Suggested solutions from Knowledge Base',
        'Este campo se completa automáticamente con el nombre de tu cuenta': 'This field is automatically filled with your account name',
        'Escribe al menos 3 caracteres en la descripción': 'Type at least 3 characters in description',
        'Comienza a escribir tu problema para ver posibles soluciones': 'Start typing your issue to see possible solutions',
        'No se encontraron artículos relacionados': 'No related articles found',
        'No se pudieron cargar sugerencias en este momento': 'Could not load suggestions right now',
        'Adjuntos': 'Attachments',
        'Formatos aceptados': 'Accepted formats',
        'Cancelar': 'Cancel',
        'Detalles': 'Details',
        'Información de SLA': 'SLA Information',
        'Vencimiento SLA': 'SLA Due',
        'Acciones Rápidas': 'Quick Actions',
        'Por categoría': 'By category',
        'Centro de Operaciones': 'Operations Hub',
        'Accesos directos interactivos para operaciones diarias': 'Interactive shortcuts for daily operations',
        'Ir a': 'Jump to',
        'Selecciona una acción': 'Select an action',
        'Cola de tickets': 'Ticket Queue',
        'Revisa todos los tickets activos': 'Review all active tickets',
        'Sigue las conversaciones en vivo': 'Follow live conversations',
        'Consulta los usuarios conectados ahora': 'See connected users now',
        'Revisa y aprueba contenido': 'Review and approve content',
        'Abre el resumen gerencial': 'Open the management summary',
        'Resumen operativo': 'Operational Snapshot',
        'Carga actual de tickets y estado de ejecución': 'Current ticket workload and execution status',
        'Productividad y riesgo': 'Productivity and Risk',
        'Velocidad de resolución, tickets reabiertos e incumplimientos de SLA': 'Resolution speed, reopened tickets and SLA breaches',
        'Calidad del servicio': 'Service Quality',
        'Indicadores de cumplimiento de SLA y satisfacción del usuario': 'SLA compliance and user satisfaction indicators',
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

    from app.billing import bp as billing_bp
    app.register_blueprint(billing_bp)

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
    configured_async_mode = os.environ.get('SOCKETIO_ASYNC_MODE', '').strip().lower()
    if configured_async_mode:
        socketio_async_mode = configured_async_mode
    else:
        # Default to threading to avoid eventlet deprecation issues in modern Python/Gunicorn.
        socketio_async_mode = 'threading'
    socketio_logging_env = os.environ.get('SOCKETIO_LOGGING')
    if socketio_logging_env is None:
        # Keep logs quiet by default in Render production; verbose locally for troubleshooting.
        socketio_logging = os.environ.get('RENDER') != 'true'
    else:
        socketio_logging = socketio_logging_env.strip().lower() in ('1', 'true', 'yes', 'on')

    socketio.init_app(
        app, 
        cors_allowed_origins='*',  # Allow WebSocket connections from anywhere
        manage_session=True,  # Allow access to Flask session and current_user
        async_mode=socketio_async_mode,
        logger=socketio_logging,
        engineio_logger=socketio_logging,
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
        return db.session.get(User, int(user_id))

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
        lang = session.get('lang', 'en')

        def _translate(text):
            return translate(text, lang)

        return {
            'current_year': utcnow().year,
            '_': _translate,
            'current_lang': lang,
            'csrf_token': generate_csrf,
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
            current_user.last_activity = utcnow()

            # Fallback presence tracking in case Socket.IO is unavailable.
            existing = online_users.get(current_user.id, {})
            online_users[current_user.id] = {
                'username': current_user.username,
                'user_role': current_user.role,
                'joined_at': existing.get('joined_at', utcnow()),
                'last_seen': utcnow(),
            }

            # Cleanup stale users (no activity in last 90 seconds).
            stale_after = utcnow() - timedelta(seconds=90)
            stale_ids = [
                uid for uid, info in online_users.items()
                if info.get('last_seen', info.get('joined_at', utcnow())) < stale_after
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
            company_columns = [col['name'] for col in inspector.get_columns('company')]

            if 'is_active' not in company_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE company ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE'))
                    conn.commit()
                app.logger.warning('Added is_active column to company table')

            if 'deactivation_reason' not in company_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE company ADD COLUMN deactivation_reason VARCHAR(255)'))
                    conn.commit()
                app.logger.warning('Added deactivation_reason column to company table')

            if 'company_id' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN company_id INTEGER'))
                    conn.commit()
                app.logger.warning('Added company_id column to user table')

            if 'is_active' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE'))
                    conn.commit()
                app.logger.warning('Added is_active column to user table')

            if 'last_activity' not in user_columns:
                with db.engine.connect() as conn:
                    # Use NULL default for SQLite compatibility (CURRENT_TIMESTAMP is non-constant in ALTER TABLE)
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN last_activity TIMESTAMP DEFAULT NULL'))
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

            if 'company_id' not in ticket_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE ticket ADD COLUMN company_id INTEGER'))
                    conn.commit()
                app.logger.warning('Added company_id column to ticket table')
            
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

            inspector = db.inspect(db.engine)

            api_token_columns = [col['name'] for col in inspector.get_columns('api_token')]
            if 'company_id' not in api_token_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE api_token ADD COLUMN company_id INTEGER'))
                    conn.commit()
                app.logger.warning('Added company_id column to api_token table')

            integration_columns = [col['name'] for col in inspector.get_columns('integration')]
            if 'company_id' not in integration_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE integration ADD COLUMN company_id INTEGER'))
                    conn.commit()
                app.logger.warning('Added company_id column to integration table')

            audit_log_columns = [col['name'] for col in inspector.get_columns('audit_log')]
            if 'company_id' not in audit_log_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE audit_log ADD COLUMN company_id INTEGER'))
                    conn.commit()
                app.logger.warning('Added company_id column to audit_log table')

            from app.models import ApiToken, Integration, AuditLog

            api_tokens_without_company = ApiToken.query.filter(ApiToken.company_id.is_(None)).all()
            for token in api_tokens_without_company:
                if token.created_by and token.created_by.company_id:
                    token.company_id = token.created_by.company_id

            integrations_without_company = Integration.query.filter(Integration.company_id.is_(None)).all()
            for integration in integrations_without_company:
                if integration.created_by and integration.created_by.company_id:
                    integration.company_id = integration.created_by.company_id

            audit_logs_without_company = AuditLog.query.filter(AuditLog.company_id.is_(None)).all()
            for log in audit_logs_without_company:
                # Evitar error si log no tiene user
                if hasattr(log, 'user') and log.user and hasattr(log.user, 'company_id') and log.user.company_id:
                    log.company_id = log.user.company_id

            db.session.commit()

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
