from flask import Flask, current_app, session, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
import logging
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


TRANSLATIONS = {
    'es': {
        'Support': 'Soporte',
        'Tickets': 'Tickets',
        'Dashboard': 'Panel',
        'Admin': 'Admin',
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
        'On time': 'En tiempo',
        'No tickets found': 'No se encontraron tickets',
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
        'Agregar un comentario...': 'Add a comment...'
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


def create_app(config_class=None):
    # Load environment variables from .env file
    load_dotenv()
    
    app = Flask(__name__)
    app.config.from_object(config_class or 'config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)

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

    @app.before_request
    def enforce_default_admin_password_change():
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

    return app


# Compatibility entrypoint for platforms configured with: gunicorn app:app
config_name = 'config.ProductionConfig' if os.environ.get('FLASK_ENV') == 'production' else 'config.Config'
app = create_app(config_name)
