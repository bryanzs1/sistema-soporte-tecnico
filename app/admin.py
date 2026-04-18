import csv
import json
from datetime import datetime, timezone
from io import StringIO


from flask import Blueprint, Response, abort, render_template, redirect, url_for, flash, request, session, current_app

bp = Blueprint('admin', __name__)

from flask_login import login_required, current_user

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import db, translate
from app.models import User, Ticket, TicketOption, ApiToken, Integration, KBArticle, KBArticleRejection, TicketComment, AuditLog, PasswordHistory, TicketAttachment, TechnicianStats
from app.forms import UserRoleForm, NewUserForm, TicketOptionForm, AdminResetPasswordForm, CompanyForm
from app.models import Company


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



@bp.route('/companies')
@login_required
@admin_required
def list_companies():
    return redirect(url_for('admin.settings_companies'))

@bp.route('/companies/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_company():
    form = CompanyForm()
    if form.validate_on_submit():
        company = Company(
            name=form.name.data.strip(),
            description=form.description.data.strip()
        )
        db.session.add(company)
        try:
            db.session.commit()
            flash(_t('Company created successfully'), 'success')
            return redirect(url_for('admin.settings_companies'))
        except IntegrityError:
            db.session.rollback()
            flash(_t('Company name already exists'), 'danger')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error('Error creating company: %s', e)
            flash(_t('Error creating company. Please try again.'), 'danger')
    return render_template('admin/edit_company.html', form=form)

@bp.route('/companies/<int:company_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_company(company_id):
    company = Company.query.get_or_404(company_id)
    form = CompanyForm(obj=company)
    if form.validate_on_submit():
        company.name = form.name.data.strip()
        company.description = form.description.data.strip()
        try:
            db.session.commit()
            flash(_t('Company updated successfully'), 'success')
            return redirect(url_for('admin.settings_companies'))
        except IntegrityError:
            db.session.rollback()
            flash(_t('Company name already exists'), 'danger')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error('Error updating company: %s', e)
            flash(_t('Error updating company. Please try again.'), 'danger')
    return render_template('admin/edit_company.html', form=form, company=company)




def utcnow():
    """Return naive UTC datetime for compatibility with current schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


def _company_ticket_query():
    return Ticket.query.filter(Ticket.company_id == current_user.company_id)


def _ticket_in_scope(ticket):
    return ticket.company_id == current_user.company_id


def _company_user_query():
    return User.query.filter(User.company_id == current_user.company_id)


def _company_user_or_404(user_id):
    return _company_user_query().filter(User.id == user_id).first_or_404()


def _company_form_choices():
    # Si el usuario es superadmin, puede ver todas las empresas
    if hasattr(current_user, 'is_superadmin') and current_user.is_superadmin():
        from app.models import Company
        return [(c.id, c.name) for c in Company.query.order_by(Company.name).all()]
    company = current_user.company
    if not company:
        return []
    return [(company.id, company.name)]


def _company_api_token_query():
    return ApiToken.query.filter(ApiToken.company_id == current_user.company_id)


def _company_api_token_or_404(token_id):
    return _company_api_token_query().filter(ApiToken.id == token_id).first_or_404()


def _company_integration_query():
    return Integration.query.filter(Integration.company_id == current_user.company_id)


def _company_integration_or_404(integration_id):
    return _company_integration_query().filter(Integration.id == integration_id).first_or_404()


def _company_audit_query():
    return AuditLog.query.filter(AuditLog.company_id == current_user.company_id)


def _company_kb_query():
    return KBArticle.query.join(User, KBArticle.created_by_id == User.id).filter(User.company_id == current_user.company_id)


def _company_kb_or_404(article_id):
    return _company_kb_query().filter(KBArticle.id == article_id).first_or_404()


def _sync_default_ticket_options():
    """Ensure default categories and priorities exist in TicketOption catalog."""
    changes = 0

    for value in Ticket.default_categories():
        normalized = (value or '').strip()
        if not normalized:
            continue
        existing = TicketOption.query.filter_by(option_type='category', value=normalized).first()
        if existing:
            if not existing.active:
                existing.active = True
                changes += 1
            continue
        db.session.add(TicketOption(option_type='category', value=normalized, active=True))
        changes += 1

    for value in Ticket.default_priorities():
        normalized = (value or '').strip()
        if not normalized:
            continue
        existing = TicketOption.query.filter_by(option_type='priority', value=normalized).first()
        if existing:
            if not existing.active:
                existing.active = True
                changes += 1
            continue
        db.session.add(TicketOption(option_type='priority', value=normalized, active=True))
        changes += 1

    if changes:
        db.session.commit()

    return changes


def _technician_reassign_enabled():
    policy = TicketOption.query.filter_by(option_type='system_policy', value='technician_reassign').first()
    return bool(policy and policy.active)


@bp.route('/ticket-options/restore-defaults', methods=['POST'])
@login_required
@admin_required
def restore_ticket_options_defaults():
    changes = _sync_default_ticket_options()
    if changes:
        flash(_t('Recommended options restored: {count}').format(count=changes), 'success')
    else:
        flash(_t('Ticket options are already up to date'), 'info')

    target = request.form.get('next')
    if target == 'settings':
        return redirect(url_for('admin.settings_ticket_options'))
    return redirect(url_for('admin.ticket_options'))


@bp.route('/users')
@login_required
@admin_required
def list_users():
    try:
        company_id = current_user.company_id
        companies = [current_user.company] if current_user.company else []
        query = _company_user_query()
        users = query.order_by(User.username).all()
        return render_template('admin/users.html', users=users, companies=companies, selected_company_id=company_id)
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error loading users list: %s', e)
        flash(_t('An unexpected error occurred'), 'danger')
        return render_template('admin/users.html', users=[], companies=[], selected_company_id=None)


@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required

def create_user():
    form = NewUserForm()
    form.company_id.choices = _company_form_choices()
    requested_company_id = current_user.company_id
    if request.method == 'GET' and requested_company_id and any(company_id == requested_company_id for company_id, _name in form.company_id.choices):
        form.company_id.data = requested_company_id

    if form.validate_on_submit():
        # Si es superadmin, puede asignar cualquier empresa; si no, solo la suya
        company_id = form.company_id.data if (hasattr(current_user, 'is_superadmin') and current_user.is_superadmin()) else current_user.company_id
        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data,
            company_id=company_id
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

        flash('User created successfully', 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('admin/edit_user.html', user=None, form=form)

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = _company_user_or_404(user_id)
    form = UserRoleForm(obj=user)
    form.company_id.choices = _company_form_choices()
    if request.method == 'GET':
        form.company_id.data = user.company_id
    if form.validate_on_submit():
        user.role = form.role.data
        user.company_id = current_user.company_id
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
    user = _company_user_or_404(user_id)
    form = AdminResetPasswordForm()

    if form.validate_on_submit():
        try:
            # Validate password strength
            from app.security import PasswordValidator, AuditHelper
            from app.models import PasswordHistory
            
            is_valid, message = PasswordValidator.validate(form.new_password.data)
            if not is_valid:
                flash(_t('Password does not meet security requirements: ') + message, 'warning')
                return render_template('admin/reset_user_password.html', user=user, form=form)
            
            # Check for password reuse
            if PasswordHistory.check_password_reuse(user.id, form.new_password.data):
                flash(_t('This password was recently used. Please choose a different one.'), 'danger')
                return render_template('admin/reset_user_password.html', user=user, form=form)
            
            # Update password and record in history using one transaction.
            old_hash = user.password_hash
            user.set_password(form.new_password.data)
            PasswordHistory.add_to_history(user.id, old_hash, commit=False)
            db.session.commit()

            # Log the password reset after persistence. Audit failures should not fail the request.
            try:
                AuditHelper.log_password_change(user.id)
            except Exception as audit_error:
                current_app.logger.warning('Audit log failed for password reset: %s', audit_error)
            
            flash(
                _t('Password for user "{username}" was reset successfully').format(username=user.username),
                'success'
            )
            return redirect(url_for('admin.settings_users'))
        
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error('Error resetting password for user %s: %s', user.username, e)
            flash(_t('Error resetting password. Please try again.'), 'danger')
            return render_template('admin/reset_user_password.html', user=user, form=form)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error('Unexpected error resetting password for user %s: %s', user.username, e)
            flash(_t('Error resetting password. Please try again.'), 'danger')
            return render_template('admin/reset_user_password.html', user=user, form=form)

    return render_template('admin/reset_user_password.html', user=user, form=form)


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = _company_user_or_404(user_id)

    # Prevent self-deletion
    if user.id == current_user.id:
        flash(_t('You cannot delete your own account.'), 'danger')
        return redirect(url_for('admin.settings_users'))

    # Prevent deleting the last admin
    if user.role == 'admin':
        admin_count = _company_user_query().filter_by(role='admin').count()
        if admin_count <= 1:
            flash(_t('Cannot delete the last administrator account.'), 'danger')
            return redirect(url_for('admin.settings_users'))

    try:
        username = user.username
        reassign_to_id = current_user.id

        # Preserve operational history by reassigning strict foreign keys to current admin.
        Ticket.query.filter_by(user_id=user.id).update({'user_id': None}, synchronize_session=False)
        Ticket.query.filter_by(technician_id=user.id).update({'technician_id': None}, synchronize_session=False)
        Ticket.query.filter_by(ml_suggested_technician_id=user.id).update({'ml_suggested_technician_id': None}, synchronize_session=False)

        TicketComment.query.filter_by(user_id=user.id).update({'user_id': reassign_to_id}, synchronize_session=False)
        TicketAttachment.query.filter_by(uploaded_by_id=user.id).update({'uploaded_by_id': reassign_to_id}, synchronize_session=False)
        KBArticle.query.filter_by(created_by_id=user.id).update({'created_by_id': reassign_to_id}, synchronize_session=False)
        KBArticleRejection.query.filter_by(rejected_by_id=user.id).update({'rejected_by_id': reassign_to_id}, synchronize_session=False)
        ApiToken.query.filter_by(created_by_id=user.id).update({'created_by_id': reassign_to_id}, synchronize_session=False)
        Integration.query.filter_by(created_by_id=user.id).update({'created_by_id': reassign_to_id}, synchronize_session=False)

        # Remove 1:1 stats and auth history tied to user.
        TechnicianStats.query.filter_by(technician_id=user.id).delete(synchronize_session=False)
        PasswordHistory.query.filter_by(user_id=user.id).delete(synchronize_session=False)

        # Nullify audit log references (nullable FK — preserves audit trail)
        AuditLog.query.filter_by(user_id=user.id).update({'user_id': None}, synchronize_session=False)

        db.session.delete(user)
        db.session.commit()
        flash(_t('User "{username}" has been permanently deleted.').format(username=username), 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('Error deleting user %s: %s', user.username, e)
        flash(_t('Error deleting user. Please try again.'), 'danger')

    return redirect(url_for('admin.settings_users'))


@bp.route('/dashboard')
@login_required
@tech_or_admin_required
def dashboard():
    # gather some ticket statistics
    from app.models import Ticket
    from datetime import datetime
    from sqlalchemy import func

    ticket_query = _company_ticket_query()
    closed_tickets = ticket_query.filter_by(status='Cerrado').all()
    resolution_hours = []
    for ticket in closed_tickets:
        if ticket.resolved_at and ticket.created_at:
            delta = ticket.resolved_at - ticket.created_at
            resolution_hours.append(delta.total_seconds() / 3600)

    avg_resolution_hours = round(sum(resolution_hours) / len(resolution_hours), 2) if resolution_hours else 0
    now = utcnow()
    overdue_count = ticket_query.filter(
        Ticket.sla_due_at.isnot(None),
        Ticket.status != 'Cerrado',
        Ticket.sla_due_at < now,
    ).count()
    reopened_total = ticket_query.filter(Ticket.reopened_count > 0).count()

    # Due soon (uses model logic — load only open tickets with sla_due_at set)
    open_with_sla = ticket_query.filter(
        Ticket.status != 'Cerrado',
        Ticket.sla_due_at.isnot(None),
    ).all()
    due_soon_count = sum(1 for t in open_with_sla if t.is_due_soon())

    # CSAT average
    csat_result = db.session.query(func.avg(Ticket.satisfaction_rating)).filter(
        Ticket.company_id == current_user.company_id,
        Ticket.satisfaction_rating.isnot(None)
    ).scalar()
    csat_avg = round(float(csat_result), 1) if csat_result else None

    # SLA compliance % (closed on time / total closed with SLA)
    closed_with_sla = ticket_query.filter(
        Ticket.status == 'Cerrado',
        Ticket.sla_due_at.isnot(None),
        Ticket.resolved_at.isnot(None),
    ).all()
    if closed_with_sla:
        on_time = sum(1 for t in closed_with_sla if t.resolved_at <= t.sla_due_at)
        sla_compliance_pct = round(100 * on_time / len(closed_with_sla), 1)
    else:
        sla_compliance_pct = None

    pending_kb_count = 0
    pending_kb_articles = []
    if current_user.is_admin():
        pending_kb_query = _company_kb_query().filter(KBArticle.is_active.is_(False)).outerjoin(
            KBArticleRejection,
            KBArticleRejection.article_id == KBArticle.id,
        ).filter(KBArticleRejection.id.is_(None))
        pending_kb_count = pending_kb_query.count()
        pending_kb_articles = pending_kb_query.order_by(KBArticle.updated_at.desc()).limit(6).all()
    elif current_user.is_technician():
        pending_kb_count = _company_kb_query().filter_by(is_active=False, created_by_id=current_user.id).outerjoin(
            KBArticleRejection,
            KBArticleRejection.article_id == KBArticle.id,
        ).filter(KBArticleRejection.id.is_(None)).count()

    stats = {
        'total': ticket_query.count(),
        'open': ticket_query.filter_by(status='Abierto').count(),
        'in_progress': ticket_query.filter_by(status='En proceso').count(),
        'waiting': ticket_query.filter_by(status='Esperando usuario').count(),
        'closed': ticket_query.filter_by(status='Cerrado').count(),
        'overdue': overdue_count,
        'avg_resolution_hours': avg_resolution_hours,
        'reopened': reopened_total,
        'due_soon': due_soon_count,
        'csat_avg': csat_avg,
        'sla_compliance_pct': sla_compliance_pct,
        'pending_kb': pending_kb_count,
    }
    # breakdown by category
    cats = {c: ticket_query.filter_by(category=c).count() for c in Ticket.categories()}
    return render_template('admin/dashboard.html', stats=stats, categories=cats,
                           pending_kb_articles=pending_kb_articles)


@bp.route('/chat-monitoring')
@login_required
@admin_required
def chat_monitoring():
    """Monitor all ticket chats with activity status"""
    from app.models import Ticket, TicketComment
    from datetime import datetime, timedelta
    
    try:
        # Get all tickets with their comment counts and last activity
        tickets = _company_ticket_query().all()
        chat_data = []
        
        for ticket in tickets:
            comments_count = TicketComment.query.filter_by(ticket_id=ticket.id).count()
            last_comment = TicketComment.query.filter_by(ticket_id=ticket.id).order_by(
                TicketComment.created_at.desc()
            ).first()
            
            last_activity = last_comment.created_at if last_comment else ticket.created_at
            # Safe datetime comparison
            try:
                is_recent = (utcnow() - last_activity).total_seconds() < 3600  # 1 hour
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
        user_obj = _company_user_query().filter(User.id == user_id).first()
        if user_obj:
            users_list.append({
                'user_id': user_id,
                'username': user_info.get('username', ''),
                'user_role': user_info.get('user_role', ''),
                'joined_at': user_info.get('joined_at', utcnow()),
                'is_active': user_obj.is_active,
            })
    
    # Sort by join time (most recent first)
    users_list.sort(key=lambda x: x['joined_at'], reverse=True)
    
    return render_template('admin/online_users.html', online_users=users_list, count=len(users_list))


@bp.route('/online-users/data')
@login_required
@admin_required
def online_users_data():
    """JSON data for live online users dashboard without full-page reload."""
    from app import online_users
    from datetime import datetime

    users_list = []
    for user_id, user_info in online_users.items():
        user_obj = _company_user_query().filter(User.id == user_id).first()
        if user_obj:
            joined_at = user_info.get('joined_at', utcnow())
            users_list.append({
                'user_id': user_id,
                'username': user_info.get('username', ''),
                'user_role': user_info.get('user_role', ''),
                'joined_at': joined_at.strftime('%H:%M:%S'),
                'is_active': user_obj.is_active,
            })

    users_list.sort(key=lambda x: x['joined_at'], reverse=True)

    return {
        'count': len(users_list),
        'online_users': users_list,
    }


@bp.route('/debug/online-users')
@login_required
@admin_required
def debug_online_users_json():
    """Debug endpoint to see raw online_users dict as JSON"""
    from app import online_users
    import json
    from datetime import datetime
    
    # Convert online_users to JSON-serializable format
    debug_data = {}
    for user_id, info in online_users.items():
        debug_data[str(user_id)] = {
            'username': info.get('username'),
            'user_role': info.get('user_role'),
            'joined_at': info.get('joined_at').isoformat() if isinstance(info.get('joined_at'), datetime) else str(info.get('joined_at')),
        }
    
    return {
        'total_online': len(online_users),
        'users': debug_data,
        'timestamp': utcnow().isoformat(),
        'message': f'Debug info for {len(online_users)} online users'
    }


@bp.route('/ticket-options', methods=['GET', 'POST'])
@login_required
@admin_required
def ticket_options():
    _sync_default_ticket_options()
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
        from app.ml_classifier import classifier, ML_AVAILABLE, ML_IMPORT_ERROR
        from app.models import TechnicianStats
        
        if not ML_AVAILABLE:
            flash(_t('Machine Learning dependencies not installed. Please run: pip install scikit-learn numpy'), 'warning')
            return render_template(
                'admin/ml_system.html',
                model_info={'trained': False, 'error': 'Dependencies not available'},
                tech_stats=[],
                ml_tickets=[],
                ml_accuracy=0,
                ml_available=False,
                ml_import_error=ML_IMPORT_ERROR
            )
        
        # Obtener información del modelo
        model_info = classifier.get_model_info()
        
        # Obtener estadísticas de técnicos
        tech_stats = TechnicianStats.query.join(User, TechnicianStats.technician_id == User.id).filter(
            User.company_id == current_user.company_id
        ).all()
        
        # Obtener tickets con predicciones ML
        ml_tickets = _company_ticket_query().filter(
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
            ml_available=True,
            ml_import_error=ML_IMPORT_ERROR
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
    """Legacy route kept for compatibility; use centralized settings page."""
    return redirect(url_for('admin.settings_integrations'))


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
        company_id=current_user.company_id,
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
    token = _company_api_token_or_404(token_id)
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
        company_id=current_user.company_id,
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
    integration = _company_integration_or_404(integration_id)
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
    integration = _company_integration_or_404(integration_id)
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
    try:
        users = _company_user_query().order_by(User.username).all()
        return render_template('admin/settings/users.html', users=users)
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error loading settings users: %s', e)
        # Fallback to legacy users view to avoid breaking admin workflow.
        try:
            users = _company_user_query().order_by(User.username).all()
        except Exception:
            db.session.rollback()
            users = []
        flash(_t('An unexpected error occurred'), 'danger')
        companies = [current_user.company] if current_user.company else []
        return render_template('admin/users.html', users=users, companies=companies, selected_company_id=current_user.company_id)


@bp.route('/settings/companies')
@login_required
@admin_required
def settings_companies():
    """Gestión de empresas desde settings"""
    companies = Company.query.order_by(Company.name).all()
    return render_template('admin/settings/companies.html', companies=companies)


@bp.route('/settings/ticket-options')
@login_required
@admin_required
def settings_ticket_options():
    """Gestión de opciones de tickets desde settings"""
    _sync_default_ticket_options()
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
                         priorities=priorities,
                         technician_reassign_enabled=_technician_reassign_enabled())


@bp.route('/settings/ticket-options/policies', methods=['POST'])
@login_required
@admin_required
def settings_ticket_policies_update():
    enabled = request.form.get('technician_reassign_enabled') == 'on'
    policy = TicketOption.query.filter_by(option_type='system_policy', value='technician_reassign').first()

    if not policy:
        policy = TicketOption(option_type='system_policy', value='technician_reassign', active=enabled)
        db.session.add(policy)
    else:
        policy.active = enabled

    db.session.commit()

    if enabled:
        flash(_t('Technicians can now reassign tickets'), 'success')
    else:
        flash(_t('Only administrators can reassign tickets'), 'info')

    return redirect(url_for('admin.settings_ticket_options'))


@bp.route('/settings/ml')
@login_required
@admin_required
def settings_ml():
    """Configuración del sistema ML desde settings"""
    try:
        from app.ml_classifier import classifier, ML_AVAILABLE, ML_IMPORT_ERROR
        
        ml_available = ML_AVAILABLE
        model_info = classifier.get_model_info() if ML_AVAILABLE else {}
        ml_accuracy = 0
        
        # Get technician stats
        from app.models import TechnicianStats
        tech_stats = TechnicianStats.query.join(User, TechnicianStats.technician_id == User.id).filter(
            User.company_id == current_user.company_id
        ).all()
        
        # Get recent tickets with ML predictions
        from app.models import Ticket
        ml_tickets = _company_ticket_query().filter(
            Ticket.ml_suggested_technician_id.isnot(None)
        ).order_by(Ticket.created_at.desc()).limit(10).all()

        if ml_tickets:
            correct_predictions = sum(
                1 for t in ml_tickets
                if t.technician_id and t.technician_id == t.ml_suggested_technician_id
            )
            ml_accuracy = (correct_predictions / len(ml_tickets)) * 100
        
        return render_template('admin/settings/ml_system.html',
                             ml_available=ml_available,
                             ml_import_error=ML_IMPORT_ERROR,
                             model_info=model_info,
                             ml_accuracy=ml_accuracy,
                             tech_stats=tech_stats,
                             ml_tickets=ml_tickets)
    except Exception as e:
        current_app.logger.error(f'Error loading ML settings: {e}')
        return render_template('admin/settings/ml_system.html',
                             ml_available=False,
                             ml_import_error=str(e),
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
    api_tokens = _company_api_token_query().order_by(ApiToken.created_at.desc()).all()
    integrations = _company_integration_query().order_by(Integration.created_at.desc()).all()
    office365_integration = _company_integration_query().filter(Integration.platform == 'office365_email').first()
    office365_config = {
        'enabled': False,
        'mailbox': '',
        'allow_external_senders': True,
    }
    if office365_integration and office365_integration.config:
        try:
            parsed = json.loads(office365_integration.config)
            office365_config.update(parsed)
        except (TypeError, ValueError):
            pass
    
    return render_template('admin/settings/integrations.html',
                         api_tokens=api_tokens,
                         integrations=integrations,
                         office365_integration=office365_integration,
                         office365_config=office365_config,
                         email_intake_url=url_for('api.office365_email_intake', _external=True))


@bp.route('/settings/audit')
@login_required
@admin_required
def settings_audit():
    """Security audit trail (read-only) with basic filters."""
    action = request.args.get('action', '').strip()
    status = request.args.get('status', '').strip()
    username = request.args.get('username', '').strip()

    q = _company_audit_query()
    if action:
        q = q.filter(AuditLog.action.ilike(f'%{action}%'))
    if status:
        q = q.filter(AuditLog.status == status)
    if username:
        q = q.join(User, User.id == AuditLog.user_id).filter(User.username.ilike(f'%{username}%'))

    logs = q.order_by(AuditLog.created_at.desc()).limit(500).all()
    return render_template('admin/settings/audit.html', logs=logs, action=action, status=status, username=username)


@bp.route('/settings/audit/export')
@login_required
@admin_required
def settings_audit_export():
    """Export audit logs to CSV for compliance review."""
    action = request.args.get('action', '').strip()
    status = request.args.get('status', '').strip()
    username = request.args.get('username', '').strip()

    q = _company_audit_query()
    if action:
        q = q.filter(AuditLog.action.ilike(f'%{action}%'))
    if status:
        q = q.filter(AuditLog.status == status)
    if username:
        q = q.join(User, User.id == AuditLog.user_id).filter(User.username.ilike(f'%{username}%'))

    logs = q.order_by(AuditLog.created_at.desc()).limit(5000).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['created_at', 'user', 'action', 'resource_type', 'resource_id', 'status', 'ip_address', 'details'])
    for log in logs:
        writer.writerow([
            log.created_at.isoformat() if log.created_at else '',
            log.user.username if log.user else '',
            log.action or '',
            log.resource_type or '',
            log.resource_id or '',
            log.status or '',
            log.ip_address or '',
            log.details or '',
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=audit_logs.csv'}
    )


@bp.route('/settings/integrations/office365-email', methods=['POST'])
@login_required
@admin_required
def settings_office365_email_update():
    """Create/update optional Office 365 email intake integration settings."""
    enabled = request.form.get('office365_enabled') == 'on'
    mailbox = request.form.get('office365_mailbox', '').strip()
    allow_external_senders = request.form.get('office365_allow_external') == 'on'

    config = {
        'enabled': enabled,
        'mailbox': mailbox,
        'allow_external_senders': allow_external_senders,
    }

    integration = _company_integration_query().filter(Integration.platform == 'office365_email').first()
    if integration:
        integration.name = 'Office 365 Email Intake'
        integration.config = json.dumps(config)
        integration.is_active = enabled
    else:
        integration = Integration(
            platform='office365_email',
            name='Office 365 Email Intake',
            company_id=current_user.company_id,
            config=json.dumps(config),
            created_by=current_user,
            is_active=enabled,
        )
        db.session.add(integration)

    db.session.commit()
    flash(_t('Office 365 email intake settings saved'), 'success')
    return redirect(url_for('admin.settings_integrations'))


# ===== KNOWLEDGE BASE =====

@bp.route('/kb')
@login_required
@tech_or_admin_required
def kb_list():
    q = request.args.get('q', '').strip()
    arts = _company_kb_query()
    if not current_user.is_admin():
        arts = arts.filter(
            (KBArticle.is_active.is_(True)) |
            ((KBArticle.is_active.is_(False)) & (KBArticle.created_by_id == current_user.id))
        )
    if q:
        like = f'%{q}%'
        arts = arts.filter(
            (KBArticle.title.ilike(like)) | (KBArticle.content.ilike(like))
        )
    articles = arts.order_by(KBArticle.is_active.desc(), KBArticle.updated_at.desc()).all()
    article_ids = [a.id for a in articles]
    rejection_map = {}
    if article_ids:
        rej_rows = KBArticleRejection.query.filter(KBArticleRejection.article_id.in_(article_ids)).all()
        rejection_map = {r.article_id: r for r in rej_rows}
    return render_template('admin/kb_list.html', articles=articles, q=q, rejection_map=rejection_map)


@bp.route('/kb/search')
@login_required
@tech_or_admin_required
def kb_search():
    q = request.args.get('q', '').strip()
    results = []
    if q:
        like = f'%{q}%'
        found = _company_kb_query().filter_by(is_active=True).filter(
            (KBArticle.title.ilike(like)) | (KBArticle.content.ilike(like))
        ).limit(8).all()
        results = [{
            'id': a.id,
            'title': a.title,
            'preview': a.content[:160] + ('...' if len(a.content) > 160 else ''),
            'content': a.content,
        } for a in found]
    from flask import jsonify
    return jsonify(results)


@bp.route('/kb/from-comment/<int:comment_id>')
@login_required
@tech_or_admin_required
def kb_from_comment(comment_id):
    comment = TicketComment.query.get_or_404(comment_id)
    ticket = comment.ticket
    if not _ticket_in_scope(ticket):
        abort(403)
    title = f"{ticket.title} - Respuesta"
    return redirect(url_for(
        'admin.kb_create',
        title=title,
        category=ticket.category or '',
        content=comment.message,
    ))


@bp.route('/kb/from-ticket/<int:ticket_id>')
@login_required
@tech_or_admin_required
def kb_from_ticket(ticket_id):
    ticket = _company_ticket_query().filter(Ticket.id == ticket_id).first_or_404()
    if ticket.status != 'Cerrado':
        flash(_t('Ticket must be closed before creating a KB article'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    best_comment = TicketComment.query.filter(
        TicketComment.ticket_id == ticket.id,
        TicketComment.user.has(User.role.in_(['admin', 'technician']))
    ).order_by(TicketComment.created_at.desc()).first()

    prefill_content = best_comment.message if best_comment else ticket.description
    title = f"{ticket.title} - Solucion"

    return redirect(url_for(
        'admin.kb_create',
        title=title,
        category=ticket.category or '',
        content=prefill_content,
    ))


@bp.route('/kb/create', methods=['GET', 'POST'])
@login_required
@tech_or_admin_required
def kb_create():
    prefill_title = request.args.get('title', '').strip()
    prefill_category = request.args.get('category', '').strip()
    prefill_content = request.args.get('content', '').strip()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', '').strip()
        if not title or not content:
            flash(_t('Title and content are required'), 'warning')
            return render_template('admin/kb_form.html', article=None,
                                   categories=[r[0] for r in _company_kb_query().with_entities(KBArticle.category).filter(KBArticle.category.isnot(None)).distinct().all()],
                                   prefill_title=title,
                                   prefill_category=category,
                                   prefill_content=content)
        article = KBArticle(
            title=title, content=content,
            category=category or None,
            created_by_id=current_user.id,
            is_active=current_user.is_admin(),
        )
        db.session.add(article)
        db.session.commit()
        flash(_t('Article created successfully') if current_user.is_admin() else _t('Article submitted for admin approval'), 'success')
        return redirect(url_for('admin.kb_list'))
    cats = [r[0] for r in _company_kb_query().with_entities(KBArticle.category).filter(KBArticle.category.isnot(None)).distinct().all()]
    return render_template('admin/kb_form.html', article=None, categories=cats,
                           prefill_title=prefill_title,
                           prefill_category=prefill_category,
                           prefill_content=prefill_content)


@bp.route('/kb/<int:article_id>/edit', methods=['GET', 'POST'])
@login_required
@tech_or_admin_required
def kb_edit(article_id):
    article = _company_kb_or_404(article_id)
    if not current_user.is_admin() and (article.created_by_id != current_user.id or article.is_active):
        flash(_t('You can only edit your own pending KB proposals'), 'warning')
        return redirect(url_for('admin.kb_list'))
    if request.method == 'POST':
        article.title = request.form.get('title', '').strip() or article.title
        article.content = request.form.get('content', '').strip() or article.content
        article.category = request.form.get('category', '').strip() or None
        if not current_user.is_admin():
            article.is_active = False
            existing_rejection = KBArticleRejection.query.filter_by(article_id=article.id).first()
            if existing_rejection:
                db.session.delete(existing_rejection)
        db.session.commit()
        flash(_t('Article updated successfully'), 'success')
        return redirect(url_for('admin.kb_list'))
    cats = [r[0] for r in _company_kb_query().with_entities(KBArticle.category).filter(KBArticle.category.isnot(None)).distinct().all()]
    return render_template('admin/kb_form.html', article=article, categories=cats)


@bp.route('/kb/<int:article_id>/delete', methods=['POST'])
@login_required
@admin_required
def kb_delete(article_id):
    article = _company_kb_or_404(article_id)
    db.session.delete(article)
    db.session.flush()
    db.session.commit()
    flash(_t('Article removed from knowledge base'), 'success')
    return redirect(url_for('admin.kb_list'))


@bp.route('/kb/<int:article_id>/approve', methods=['POST'])
@login_required
@admin_required
def kb_approve(article_id):
    article = _company_kb_or_404(article_id)
    article.is_active = True
    existing_rejection = KBArticleRejection.query.filter_by(article_id=article.id).first()
    if existing_rejection:
        db.session.delete(existing_rejection)
    db.session.commit()
    flash(_t('Article approved and published'), 'success')
    return redirect(url_for('admin.kb_list'))


@bp.route('/kb/<int:article_id>/reject', methods=['POST'])
@login_required
@admin_required
def kb_reject(article_id):
    article = _company_kb_or_404(article_id)
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash(_t('Please provide a rejection reason'), 'warning')
        return redirect(url_for('admin.kb_list'))

    article.is_active = False
    existing_rejection = KBArticleRejection.query.filter_by(article_id=article.id).first()
    if existing_rejection:
        existing_rejection.reason = reason
        existing_rejection.rejected_by_id = current_user.id
    else:
        db.session.add(KBArticleRejection(
            article_id=article.id,
            reason=reason,
            rejected_by_id=current_user.id,
        ))
    db.session.commit()
    flash(_t('Article rejected with feedback'), 'info')
    return redirect(url_for('admin.kb_list'))


# ===== EXECUTIVE REPORT =====

@bp.route('/report')
@login_required
@tech_or_admin_required
def executive_report():
    from app.models import Ticket
    from datetime import datetime, timedelta
    from sqlalchemy import func

    now = utcnow()
    week_start = now - timedelta(days=7)
    prev_week_start = now - timedelta(days=14)

    all_tickets = _company_ticket_query().all()
    open_tickets = [t for t in all_tickets if t.status != 'Cerrado']
    closed_tickets = [t for t in all_tickets if t.status == 'Cerrado']

    # SLA compliance
    closed_with_sla = [t for t in closed_tickets if t.sla_due_at and t.resolved_at]
    sla_compliance = round(100 * sum(1 for t in closed_with_sla if t.resolved_at <= t.sla_due_at) / len(closed_with_sla), 1) if closed_with_sla else None

    # Avg resolution hours
    res_hours = [(t.resolved_at - t.created_at).total_seconds() / 3600 for t in closed_tickets if t.resolved_at and t.created_at]
    avg_resolution_hours = round(sum(res_hours) / len(res_hours), 1) if res_hours else None

    # CSAT
    csat_result = db.session.query(func.avg(Ticket.satisfaction_rating)).filter(
        Ticket.company_id == current_user.company_id,
        Ticket.satisfaction_rating.isnot(None),
    ).scalar()
    csat_avg = round(float(csat_result), 1) if csat_result else None

    # Overdue & due soon
    overdue = [t for t in open_tickets if t.is_overdue()]
    due_soon = [t for t in open_tickets if t.is_due_soon()]

    # By category
    by_category = {}
    for t in all_tickets:
        by_category[t.category or '—'] = by_category.get(t.category or '—', 0) + 1

    # By priority
    by_priority = {}
    for t in all_tickets:
        by_priority[t.priority or '—'] = by_priority.get(t.priority or '—', 0) + 1

    # By technician (closed tickets)
    by_tech = {}
    for t in closed_tickets:
        name = t.technician.username if t.technician else '—'
        by_tech[name] = by_tech.get(name, 0) + 1

    # This week vs last week
    this_week = [t for t in all_tickets if t.created_at and t.created_at >= week_start]
    prev_week = [t for t in all_tickets if t.created_at and prev_week_start <= t.created_at < week_start]
    this_week_closed = [t for t in this_week if t.status == 'Cerrado']
    prev_week_closed = [t for t in prev_week if t.status == 'Cerrado']

    return render_template('admin/executive_report.html',
        now=now,
        generated_on=now.strftime('%Y-%m-%d %H:%M'),
        total=len(all_tickets),
        open_count=len(open_tickets),
        closed_count=len(closed_tickets),
        overdue_count=len(overdue),
        due_soon_count=len(due_soon),
        sla_compliance=sla_compliance,
        avg_resolution=avg_resolution_hours,
        avg_resolution_hours=avg_resolution_hours,
        csat_avg=csat_avg,
        by_category=by_category,
        by_priority=by_priority,
        by_tech=by_tech,
        this_week_created=len(this_week),
        this_week_closed=len(this_week_closed),
        prev_week_created=len(prev_week),
        prev_week_closed=len(prev_week_closed),
        overdue_tickets=overdue,
    )
