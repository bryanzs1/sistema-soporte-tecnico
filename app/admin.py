from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_required, current_user

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import db, translate
from app.models import User, TicketOption, ApiToken, Integration
from app.forms import UserRoleForm, NewUserForm, TicketOptionForm, AdminResetPasswordForm

bp = Blueprint('admin', __name__)


def _t(text):
    return translate(text, session.get('lang', 'en'))


def admin_required(func):
    """Decorator to restrict access to admins."""
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash(_t('Administrator access required'), 'warning')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)

    return wrapper


def tech_or_admin_required(func):
    """Permit only technicians or administrators."""
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_admin() or current_user.is_technician()):
            flash(_t('Technician or admin access required'), 'warning')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)

    return wrapper


@bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users)


@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required

def create_user():
    form = NewUserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(_t('Username or email already exists'), 'danger')
            return render_template('admin/edit_user.html', user=None, form=form)
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error('Error creating user: %s', e)
            flash(_t('Error creating user. Please try again.'), 'danger')
            return render_template('admin/edit_user.html', user=None, form=form)

        flash(_t('User "{username}" created successfully with role: {role}').format(username=user.username, role=user.role), 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('admin/edit_user.html', user=None, form=form)

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserRoleForm(obj=user)
    if form.validate_on_submit():
        user.role = form.role.data
        user.is_active = form.is_active.data
        db.session.commit()
        status = _t('Active') if user.is_active else _t('Inactive')
        flash(_t('User "{username}" updated - Role: {role}, Status: {status}').format(username=user.username, role=user.role, status=status), 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('admin/edit_user.html', user=user, form=form)


@bp.route('/users/<int:user_id>/reset-password', methods=['GET', 'POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        db.session.commit()
        flash(
            _t('Password for user "{username}" was reset successfully').format(username=user.username),
            'success'
        )
        return redirect(url_for('admin.list_users'))

    return render_template('admin/reset_user_password.html', user=user, form=form)


@bp.route('/dashboard')
@login_required
@tech_or_admin_required
def dashboard():
    # gather some ticket statistics
    from app.models import Ticket
    from datetime import datetime

    closed_tickets = Ticket.query.filter_by(status='Cerrado').all()
    resolution_hours = []
    for ticket in closed_tickets:
        if ticket.resolved_at and ticket.created_at:
            delta = ticket.resolved_at - ticket.created_at
            resolution_hours.append(delta.total_seconds() / 3600)

    avg_resolution_hours = round(sum(resolution_hours) / len(resolution_hours), 2) if resolution_hours else 0
    overdue_count = Ticket.query.filter(
        Ticket.sla_due_at.isnot(None),
        Ticket.status != 'Cerrado',
        Ticket.sla_due_at < datetime.utcnow(),
    ).count()
    reopened_total = Ticket.query.filter(Ticket.reopened_count > 0).count()

    stats = {
        'total': Ticket.query.count(),
        'open': Ticket.query.filter_by(status='Abierto').count(),
        'in_progress': Ticket.query.filter_by(status='En proceso').count(),
        'waiting': Ticket.query.filter_by(status='Esperando usuario').count(),
        'closed': Ticket.query.filter_by(status='Cerrado').count(),
        'overdue': overdue_count,
        'avg_resolution_hours': avg_resolution_hours,
        'reopened': reopened_total,
    }
    # breakdown by category
    cats = {c: Ticket.query.filter_by(category=c).count() for c in Ticket.categories()}
    return render_template('admin/dashboard.html', stats=stats, categories=cats)


@bp.route('/chat-monitoring')
@login_required
@admin_required
def chat_monitoring():
    """Monitor all ticket chats with activity status"""
    from app.models import Ticket, TicketComment
    from datetime import datetime, timedelta
    
    try:
        # Get all tickets with their comment counts and last activity
        tickets = Ticket.query.all()
        chat_data = []
        
        for ticket in tickets:
            comments_count = TicketComment.query.filter_by(ticket_id=ticket.id).count()
            last_comment = TicketComment.query.filter_by(ticket_id=ticket.id).order_by(
                TicketComment.created_at.desc()
            ).first()
            
            last_activity = last_comment.created_at if last_comment else ticket.created_at
            # Safe datetime comparison
            try:
                is_recent = (datetime.utcnow() - last_activity).total_seconds() < 3600  # 1 hour
            except:
                is_recent = False
            
            chat_data.append({
                'ticket': ticket,
                'message_count': comments_count,
                'last_activity': last_activity,
                'is_recent': is_recent,
                'participant_names': _get_chat_participants(ticket),
            })
        
        # Sort by last activity (most recent first)
        chat_data.sort(key=lambda x: x['last_activity'], reverse=True)
        
        return render_template('admin/chat_monitoring.html', chat_data=chat_data)
    except Exception as e:
        current_app.logger.error(f'Chat monitoring error: {e}')
        flash(_t('Error loading chat monitoring'), 'danger')
        return redirect(url_for('admin.dashboard'))


def _get_chat_participants(ticket):
    """Get unique participants in a ticket's chat with separation by role"""
    from app.models import TicketComment
    try:
        comments = TicketComment.query.filter_by(ticket_id=ticket.id).all()
        all_participants = set()
        
        if ticket.user:
            all_participants.add(ticket.user.username)
        if ticket.technician:
            all_participants.add(ticket.technician.username)
        for comment in comments:
            if comment.user:
                all_participants.add(comment.user.username)
        
        # Calculate "other" participants (excluding client and technician)
        other_participants = []
        if ticket.user:
            other_participants = [p for p in all_participants if p != ticket.user.username and (not ticket.technician or p != ticket.technician.username)]
        elif ticket.technician:
            other_participants = [p for p in all_participants if p != ticket.technician.username]
        else:
            other_participants = list(all_participants)
        
        return {
            'all': list(all_participants),
            'others': other_participants,
        }
    except:
        return {'all': [], 'others': []}


@bp.route('/online-users')
@login_required
@admin_required
def online_users_list():
    """Display all currently online users"""
    from app import online_users
    from datetime import datetime
    
    # Get list of online users with their info
    users_list = []
    for user_id, user_info in online_users.items():
        user_obj = User.query.get(user_id)
        if user_obj:
            users_list.append({
                'user_id': user_id,
                'username': user_info.get('username', ''),
                'user_role': user_info.get('user_role', ''),
                'joined_at': user_info.get('joined_at', datetime.utcnow()),
                'is_active': user_obj.is_active,
            })
    
    # Sort by join time (most recent first)
    users_list.sort(key=lambda x: x['joined_at'], reverse=True)
    
    return render_template('admin/online_users.html', online_users=users_list, count=len(users_list))


@login_required
@admin_required
def ticket_options():
    form = TicketOptionForm()
    if form.validate_on_submit():
        exists = TicketOption.query.filter_by(
            option_type=form.option_type.data,
            value=form.value.data.strip()
        ).first()
        if exists:
            exists.active = True
            flash(_t('Option already existed and was reactivated'), 'info')
        else:
            item = TicketOption(option_type=form.option_type.data, value=form.value.data.strip(), active=True)
            db.session.add(item)
            flash(_t('Option "{value}" added to {type}').format(value=form.value.data.strip(), type=form.option_type.data), 'success')
        db.session.commit()
        return redirect(url_for('admin.ticket_options'))

    categories = TicketOption.query.filter_by(option_type='category', active=True).order_by(TicketOption.value.asc()).all()
    priorities = TicketOption.query.filter_by(option_type='priority', active=True).order_by(TicketOption.value.asc()).all()
    return render_template('admin/ticket_options.html', form=form, categories=categories, priorities=priorities)


@bp.route('/ticket-options/<int:option_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_ticket_option(option_id):
    option = TicketOption.query.get_or_404(option_id)
    option.active = False
    db.session.commit()
    flash(_t('Option "{value}" removed').format(value=option.value), 'info')
    return redirect(url_for('admin.ticket_options'))


@bp.route('/ticket-options/<int:option_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_ticket_option(option_id):
    option = TicketOption.query.get_or_404(option_id)
    new_value = (request.form.get('value') or '').strip()

    if not new_value:
        flash(_t('Value is required'), 'danger')
        return redirect(url_for('admin.ticket_options'))

    duplicate = TicketOption.query.filter(
        TicketOption.option_type == option.option_type,
        TicketOption.value == new_value,
        TicketOption.id != option.id,
        TicketOption.active.is_(True)
    ).first()
    if duplicate:
        flash(_t('Option already exists'), 'warning')
        return redirect(url_for('admin.ticket_options'))

    option.value = new_value
    db.session.commit()
    flash(_t('Option updated to "{value}"').format(value=new_value), 'success')
    return redirect(url_for('admin.ticket_options'))

@bp.route('/ml-system')
@login_required
@admin_required
def ml_system():
    """Página de administración del sistema ML"""
    try:
        from app.ml_classifier import classifier, ML_AVAILABLE
        from app.models import TechnicianStats
        
        if not ML_AVAILABLE:
            flash(_t('Machine Learning dependencies not installed. Please run: pip install scikit-learn numpy'), 'warning')
            return render_template(
                'admin/ml_system.html',
                model_info={'trained': False, 'error': 'Dependencies not available'},
                tech_stats=[],
                ml_tickets=[],
                ml_accuracy=0,
                ml_available=False
            )
        
        # Obtener información del modelo
        model_info = classifier.get_model_info()
        
        # Obtener estadísticas de técnicos
        tech_stats = TechnicianStats.query.all()
        
        # Obtener tickets con predicciones ML
        ml_tickets = Ticket.query.filter(
            Ticket.ml_suggested_technician_id.isnot(None)
        ).order_by(Ticket.created_at.desc()).limit(20).all()
        
        # Calcular precisión del modelo (tickets donde la sugerencia coincide con la asignación final)
        if ml_tickets:
            correct_predictions = sum(
                1 for t in ml_tickets 
                if t.technician_id and t.technician_id == t.ml_suggested_technician_id
            )
            ml_accuracy = (correct_predictions / len(ml_tickets)) * 100 if ml_tickets else 0
        else:
            ml_accuracy = 0
        
        return render_template(
            'admin/ml_system.html',
            model_info=model_info,
            tech_stats=tech_stats,
            ml_tickets=ml_tickets,
            ml_accuracy=ml_accuracy,
            ml_available=True
        )
    except Exception as e:
        current_app.logger.error(f'Error in ML system: {e}')
        flash(_t('An error occurred loading the ML system'), 'danger')
        return redirect(url_for('admin.dashboard'))


@bp.route('/ml-system/train', methods=['POST'])
@login_required
@admin_required
def ml_train():
    """Entrena el modelo ML"""
    from app.ml_classifier import classifier
    
    result = classifier.train(min_tickets=10)
    
    if result['success']:
        flash(_t('ML model trained successfully! Accuracy: {accuracy:.1%}').format(accuracy=result['accuracy']), 'success')
    else:
        flash(_t('Error training model: {error}').format(error=result.get('error', 'Unknown error')), 'danger')
    
    return redirect(url_for('admin.ml_system'))


@bp.route('/integrations')
@login_required
@admin_required
def integrations():
    """Gestión de integraciones y API tokens"""
    api_tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    integrations = Integration.query.order_by(Integration.created_at.desc()).all()
    
    return render_template('admin/integrations.html', 
                         api_tokens=api_tokens,
                         integrations=integrations)


@bp.route('/integrations/tokens/create', methods=['POST'])
@login_required
@admin_required
def create_api_token():
    """Crea un nuevo API token"""
    import secrets
    
    name = request.form.get('name', '').strip()
    
    if not name:
        flash(_t('Token name is required'), 'danger')
        return redirect(url_for('admin.integrations'))
    
    # Generar token seguro
    token_value = secrets.token_urlsafe(32)
    
    # Crear el token
    token = ApiToken(
        name=name,
        token=token_value,
        created_by=current_user,
        is_active=True
    )
    
    db.session.add(token)
    db.session.commit()
    
    flash(_t('API token created successfully. Save it now, it won\'t be shown again: {token}').format(token=token_value), 'success')
    return redirect(url_for('admin.integrations'))


@bp.route('/integrations/tokens/<int:token_id>/revoke', methods=['POST'])
@login_required
@admin_required
def revoke_api_token(token_id):
    """Revoca un API token"""
    token = ApiToken.query.get_or_404(token_id)
    token.is_active = False
    db.session.commit()
    
    flash(_t('API token revoked'), 'success')
    return redirect(url_for('admin.integrations'))


@bp.route('/integrations/create', methods=['POST'])
@login_required
@admin_required
def create_integration():
    """Crea una nueva integración"""
    import json
    
    platform = request.form.get('platform', '').strip()
    name = request.form.get('name', '').strip()
    webhook_url = request.form.get('webhook_url', '').strip()
    verification_token = request.form.get('verification_token', '').strip()
    
    if not platform or not name:
        flash(_t('Platform and name are required'), 'danger')
        return redirect(url_for('admin.integrations'))
    
    # Configuración adicional
    config = {}
    if verification_token:
        config['verification_token'] = verification_token
    
    integration = Integration(
        platform=platform,
        name=name,
        webhook_url=webhook_url,
        config=json.dumps(config) if config else None,
        created_by=current_user,
        is_active=True
    )
    
    db.session.add(integration)
    db.session.commit()
    
    flash(_t('Integration created successfully'), 'success')
    return redirect(url_for('admin.integrations'))


@bp.route('/integrations/<int:integration_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_integration(integration_id):
    """Activa/desactiva una integración"""
    integration = Integration.query.get_or_404(integration_id)
    integration.is_active = not integration.is_active
    db.session.commit()
    
    status = _t('activated') if integration.is_active else _t('deactivated')
    flash(_t('Integration {status}').format(status=status), 'success')
    return redirect(url_for('admin.integrations'))


@bp.route('/integrations/<int:integration_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_integration(integration_id):
    """Elimina una integración"""
    integration = Integration.query.get_or_404(integration_id)
    db.session.delete(integration)
    db.session.commit()
    
    flash(_t('Integration deleted'), 'success')
    return redirect(url_for('admin.integrations'))


@bp.route('/ai-system')
@login_required
@admin_required
def ai_system():
    """Panel de control del sistema IA"""
    from app.ai_sentiment import get_analyzer
    from app.ai_chatbot import get_chatbot
    
    # Get settings from session or DB
    ai_settings = session.get('ai_settings', {
        'sentiment_enabled': True,
        'chatbot_enabled': True,
        'chatbot_confidence_threshold': 0.75
    })
    
    analyzer = get_analyzer()
    chatbot = get_chatbot()
    
    return render_template('admin/ai_system.html',
                         ai_settings=ai_settings,
                         sentiment_available=analyzer.available,
                         chatbot_categories=chatbot.get_all_categories())


@bp.route('/ai-system/settings', methods=['POST'])
@login_required
@admin_required
def ai_system_settings():
    """Actualizar configuración de IA"""
    from app.models import db
    
    # Actualizar configuración en sesión (en producción, usar DB)
    ai_settings = {
        'sentiment_enabled': request.form.get('sentiment_enabled') == 'on',
        'chatbot_enabled': request.form.get('chatbot_enabled') == 'on',
        'chatbot_confidence_threshold': float(request.form.get('chatbot_threshold', 0.75))
    }
    
    session['ai_settings'] = ai_settings
    flash(_t('AI System Settings updated'), 'success')
    return redirect(url_for('admin.ai_system'))


# ==================== SETTINGS AREA ====================
# Nueva área de configuración centralizada

@bp.route('/settings')
@login_required
@admin_required
def settings():
    """Página principal de configuración"""
    return render_template('admin/settings/index.html')


@bp.route('/settings/users')
@login_required
@admin_required
def settings_users():
    """Gestión de usuarios desde settings"""
    users = User.query.order_by(User.username).all()
    return render_template('admin/settings/users.html', users=users)


@bp.route('/settings/ticket-options')
@login_required
@admin_required
def settings_ticket_options():
    """Gestión de opciones de tickets desde settings"""
    form = TicketOptionForm()
    categories = TicketOption.query.filter_by(option_type='category', active=True).all()
    priorities = TicketOption.query.filter_by(option_type='priority', active=True).all()
    
    if form.validate_on_submit():
        try:
            existing = TicketOption.query.filter_by(
                option_type=form.option_type.data,
                value=form.value.data
            ).first()
            
            if existing and existing.active:
                flash(_t('Option already exists'), 'warning')
            elif existing and not existing.active:
                existing.active = True
                db.session.commit()
                flash(_t('Option already existed and was reactivated'), 'success')
            else:
                option = TicketOption(option_type=form.option_type.data, value=form.value.data)
                db.session.add(option)
                db.session.commit()
                flash(_t('Option added'), 'success')
        except Exception as e:
            db.session.rollback()
            flash(_t('Error adding option: {error}').format(error=str(e)), 'danger')
        
        return redirect(url_for('admin.settings_ticket_options'))
    
    return render_template('admin/settings/ticket_options.html', 
                         form=form, 
                         categories=categories, 
                         priorities=priorities)


@bp.route('/settings/ml')
@login_required
@admin_required
def settings_ml():
    """Configuración del sistema ML desde settings"""
    try:
        from app.ml_classifier import classifier, ML_AVAILABLE
        
        ml_available = ML_AVAILABLE
        model_info = classifier.model_info() if ML_AVAILABLE else {}
        ml_accuracy = classifier.accuracy if ML_AVAILABLE else 0
        
        # Get technician stats
        from app.models import TechnicianStats
        tech_stats = TechnicianStats.query.all()
        
        # Get recent tickets with ML predictions
        from app.models import Ticket
        ml_tickets = Ticket.query.filter(
            Ticket.ml_suggested_technician_id.isnot(None)
        ).order_by(Ticket.created_at.desc()).limit(10).all()
        
        return render_template('admin/settings/ml_system.html',
                             ml_available=ml_available,
                             model_info=model_info,
                             ml_accuracy=ml_accuracy,
                             tech_stats=tech_stats,
                             ml_tickets=ml_tickets)
    except Exception as e:
        current_app.logger.error(f'Error loading ML settings: {e}')
        return render_template('admin/settings/ml_system.html',
                             ml_available=False,
                             model_info={},
                             ml_accuracy=0,
                             tech_stats=[],
                             ml_tickets=[])


@bp.route('/settings/ai')
@login_required
@admin_required
def settings_ai():
    """Configuración del sistema IA desde settings"""
    from app.ai_sentiment import get_analyzer
    from app.ai_chatbot import get_chatbot
    
    # Get settings from session or DB
    ai_settings = session.get('ai_settings', {
        'sentiment_enabled': True,
        'chatbot_enabled': True,
        'chatbot_confidence_threshold': 0.75
    })
    
    analyzer = get_analyzer()
    chatbot = get_chatbot()
    
    return render_template('admin/settings/ai_system.html',
                         ai_settings=ai_settings,
                         sentiment_available=analyzer.available,
                         chatbot_categories=chatbot.get_all_categories())


@bp.route('/settings/ai/settings', methods=['POST'])
@login_required
@admin_required
def settings_ai_update():
    """Actualizar configuración de IA desde settings"""
    ai_settings = {
        'sentiment_enabled': request.form.get('sentiment_enabled') == 'on',
        'chatbot_enabled': request.form.get('chatbot_enabled') == 'on',
        'chatbot_confidence_threshold': float(request.form.get('chatbot_threshold', 0.75))
    }
    
    session['ai_settings'] = ai_settings
    flash(_t('AI System Settings updated'), 'success')
    return redirect(url_for('admin.settings_ai'))


@bp.route('/settings/integrations')
@login_required
@admin_required
def settings_integrations():
    """Gestión de integraciones desde settings"""
    api_tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    integrations = Integration.query.order_by(Integration.created_at.desc()).all()
    
    return render_template('admin/settings/integrations.html',
                         api_tokens=api_tokens,
                         integrations=integrations)

