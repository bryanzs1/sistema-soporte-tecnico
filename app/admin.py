from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user

from app import db, translate
from app.models import User, TicketOption
from app.forms import UserRoleForm, NewUserForm, TicketOptionForm

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
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
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
        db.session.commit()
        flash(_t('User "{username}" updated - New role: {role}').format(username=user.username, role=user.role), 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('admin/edit_user.html', user=user, form=form)


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


@bp.route('/ticket-options', methods=['GET', 'POST'])
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
