import os
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, current_app, session, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db, translate
from app.models import Ticket, User, TicketComment, TicketAttachment
from app.forms import TicketForm, TicketUpdateForm, TicketCommentForm

bp = Blueprint('tickets', __name__)


def _t(text):
    return translate(text, session.get('lang', 'en'))


def _attachments_dir():
    # In Render, use persistent storage at /mnt/data
    # In development, use instance/uploads
    if os.environ.get('RENDER') == 'true':
        upload_dir = '/mnt/data/uploads'
    else:
        upload_dir = os.path.join(current_app.instance_path, 'uploads')
    
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _save_attachment(file_storage, ticket_id):
    if not file_storage or not file_storage.filename:
        return None

    original_filename = secure_filename(file_storage.filename)
    if not original_filename:
        return None

    ext = os.path.splitext(original_filename)[1]
    stored_filename = f"ticket_{ticket_id}_{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(_attachments_dir(), stored_filename)
    file_storage.save(full_path)

    size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        uploaded_by_id=current_user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=file_storage.content_type,
        file_size=size,
    )
    db.session.add(attachment)
    return attachment


@bp.route('/')
@login_required
def list_tickets():
    try:
        # start with base query depending on role
        if current_user.is_admin() or current_user.is_technician():
            q = Ticket.query
        else:
            q = Ticket.query.filter_by(user_id=current_user.id)

        # apply filters from query string
        status = request.args.get('status', type=str)
        category = request.args.get('category', type=str)
        priority = request.args.get('priority', type=str)
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)
        keyword = request.args.get('keyword', type=str)

        if status:
            q = q.filter_by(status=status)
        if category:
            q = q.filter_by(category=category)
        if priority:
            q = q.filter_by(priority=priority)
        if start_date:
            try:
                from datetime import datetime
                sd = datetime.fromisoformat(start_date)
                q = q.filter(Ticket.created_at >= sd)
            except ValueError:
                pass
        if end_date:
            try:
                from datetime import datetime
                ed = datetime.fromisoformat(end_date)
                q = q.filter(Ticket.created_at <= ed)
            except ValueError:
                pass
        if keyword:
            kw = f"%{keyword}%"
            q = q.filter((Ticket.title.ilike(kw)) | (Ticket.description.ilike(kw)))

        tickets = q.order_by(Ticket.created_at.desc()).all()

        # Get categories and priorities safely
        categories = Ticket.categories()
        priorities = Ticket.priorities()

        return render_template('tickets/list.html', tickets=tickets,
                               status=status, category=category, priority=priority,
                               start_date=start_date, end_date=end_date, keyword=keyword,
                               categories=categories, priorities=priorities)
    except Exception as e:
        current_app.logger.exception('Error rendering tickets list: %s', e)
        # fallback response to avoid 500 after creating tickets
        return render_template('tickets/list.html', tickets=[],
                               status=None, category=None, priority=None,
                               start_date=None, end_date=None, keyword=None,
                               categories=Ticket.default_categories(),
                               priorities=Ticket.default_priorities())


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    form = TicketForm()
    if form.validate_on_submit():
        ticket = Ticket(
            title=form.title.data,
            creator_name=form.creator_name.data,
            description=form.description.data,
            category=form.category.data,
            priority=form.priority.data,
            user=current_user
        )
        ticket.sla_due_at = datetime.utcnow() + timedelta(hours=Ticket.sla_hours_by_priority(ticket.priority))
        
        # ML: Obtener sugerencia de técnico
        try:
            from app.ml_classifier import classifier
            
            ticket_data = {
                'title': ticket.title,
                'description': ticket.description,
                'category': ticket.category or 'Otro',
                'priority': ticket.priority or 'Media'
            }
            
            predictions = classifier.predict(ticket_data, top_n=1)
            
            if predictions:
                suggested_tech_id, confidence = predictions[0]
                ticket.ml_suggested_technician_id = suggested_tech_id
                ticket.ml_confidence_score = confidence
                
                # Auto-asignar si la confianza es muy alta (>70%)
                if confidence > 0.7:
                    ticket.technician_id = suggested_tech_id
                    ticket.auto_assigned = True
        except Exception as e:
            # Si falla el ML, no afecta la creación del ticket
            current_app.logger.warning(f'ML prediction failed: {e}')
        
        db.session.add(ticket)
        db.session.commit()

        _save_attachment(form.attachment.data, ticket.id)
        db.session.commit()

        # Redirect to detail page to avoid post-create list rendering failures
        flash(_t('Ticket created successfully'), 'success')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))
    return render_template('tickets/create.html', form=form)


@bp.route('/request-password-reset')
@login_required
def request_password_reset_ticket():
    if current_user.is_admin() or current_user.is_technician():
        flash(_t('This option is only for normal users'), 'warning')
        return redirect(url_for('tickets.list_tickets'))

    categories = Ticket.categories()
    priorities = Ticket.priorities()

    category = 'Software' if 'Software' in categories else (categories[0] if categories else 'Software')
    priority = 'Alta' if 'Alta' in priorities else (priorities[0] if priorities else 'Alta')

    ticket = Ticket(
        title=_t('Password reset request'),
        creator_name=current_user.username,
        description=_t('User requested password reset. Registered email: {email}').format(email=current_user.email),
        category=category,
        priority=priority,
        user=current_user,
    )
    ticket.sla_due_at = datetime.utcnow() + timedelta(hours=Ticket.sla_hours_by_priority(ticket.priority))
    
    # ML: Obtener sugerencia de técnico
    try:
        from app.ml_classifier import classifier
        
        ticket_data = {
            'title': ticket.title,
            'description': ticket.description,
            'category': category,
            'priority': priority
        }
        
        predictions = classifier.predict(ticket_data, top_n=1)
        
        if predictions:
            suggested_tech_id, confidence = predictions[0]
            ticket.ml_suggested_technician_id = suggested_tech_id
            ticket.ml_confidence_score = confidence
            
            # Auto-asignar si la confianza es muy alta (>70%)
            if confidence > 0.7:
                ticket.technician_id = suggested_tech_id
                ticket.auto_assigned = True
    except Exception as e:
        # Si falla el ML, no afecta la creación del ticket
        current_app.logger.warning(f'ML prediction failed: {e}')
    
    db.session.add(ticket)
    db.session.commit()

    flash(_t('Password reset ticket created successfully'), 'success')
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))


@bp.route('/attachments/<int:attachment_id>/download')
@login_required
def download_attachment(attachment_id):
    attachment = TicketAttachment.query.get_or_404(attachment_id)
    ticket = attachment.ticket
    allowed = current_user.is_admin() or current_user.is_technician() or ticket.user_id == current_user.id
    if not allowed:
        abort(403)

    return send_from_directory(
        _attachments_dir(),
        attachment.stored_filename,
        as_attachment=True,
        download_name=attachment.original_filename,
    )


@bp.route('/export')
@login_required
def export_tickets():
    # reuse same filter logic as list_tickets
    if current_user.is_admin() or current_user.is_technician():
        q = Ticket.query
    else:
        q = Ticket.query.filter_by(user_id=current_user.id)
    status = request.args.get('status', type=str)
    category = request.args.get('category', type=str)
    priority = request.args.get('priority', type=str)
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    keyword = request.args.get('keyword', type=str)
    fmt = request.args.get('format', 'csv')  # csv or xlsx
    # common imports
    import io

    if status:
        q = q.filter_by(status=status)
    if category:
        q = q.filter_by(category=category)
    if priority:
        q = q.filter_by(priority=priority)
    if start_date:
        try:
            from datetime import datetime
            sd = datetime.fromisoformat(start_date)
            q = q.filter(Ticket.created_at >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import datetime
            ed = datetime.fromisoformat(end_date)
            q = q.filter(Ticket.created_at <= ed)
        except ValueError:
            pass
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter((Ticket.title.ilike(kw)) | (Ticket.description.ilike(kw)))
    tickets = q.order_by(Ticket.created_at.desc()).all()

    # prepare data table
    data = []
    for t in tickets:
        data.append({
            'ID': t.id,
            'Title': t.title,
            'Creator': t.creator_name,
            'Status': t.status,
            'Priority': t.priority,
            'Category': t.category,
            'Created At': t.created_at,
            'User': t.user.username if t.user else '',
            'Technician': t.technician.username if t.technician else ''
        })

    if fmt == 'xlsx':
        # generate excel via pandas
        try:
            import pandas as pd
        except ImportError:
            return _t('pandas required for excel export'), 500
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return Response(output.read(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        headers={"Content-Disposition": "attachment;filename=tickets.xlsx"})
    else:
        # csv default
        import csv, io
        si = io.StringIO()
        writer = csv.writer(si)
        if data:
            writer.writerow(data[0].keys())
            for row in data:
                writer.writerow(row.values())
        output = si.getvalue()
        return Response(output, mimetype='text/csv',
                        headers={"Content-Disposition": "attachment;filename=tickets.csv"})


@bp.route('/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    # authorization: owner or tech/admin
    if not (current_user.is_admin() or current_user.is_technician() or ticket.user_id == current_user.id):
        flash(_t('You do not have access to this ticket'), 'danger')
        return redirect(url_for('tickets.list_tickets'))

    form = TicketUpdateForm()
    comment_form = TicketCommentForm(prefix='comment')
    # populate technician choices only for admin/tech
    if current_user.is_admin() or current_user.is_technician():
        # Get active technicians who are currently online (active within last 30 minutes)
        from datetime import datetime, timedelta
        thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
        techs = User.query.filter(
            User.role == 'technician',
            User.is_active == True,
            User.last_activity >= thirty_min_ago
        ).order_by(User.username).all()
        # Add "Unassigned" option first
        form.technician.choices = [(0, _t('-- Unassigned --'))] + [(t.id, f"{t.username} (online)") for t in techs]
    else:
        form.technician.choices = []

    comment_submit_pressed = (
        'submit_comment' in request.form
        or 'comment-submit_comment' in request.form
        or comment_form.submit_comment.name in request.form
    )
    if comment_submit_pressed and comment_form.validate_on_submit():
        comment = TicketComment(ticket_id=ticket.id, user_id=current_user.id, message=comment_form.message.data.strip())
        db.session.add(comment)
        db.session.commit()
        flash(_t('Comment added'), 'success')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    if request.method == 'POST' and not comment_submit_pressed and (current_user.is_admin() or current_user.is_technician()):
        previous_status = ticket.status

        submitted_status = request.form.get('status')
        if submitted_status not in Ticket.statuses():
            flash(_t('Ticket updated'), 'warning')
            return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

        ticket.status = submitted_status

        submitted_technician = request.form.get('technician')
        if submitted_technician and str(submitted_technician).isdigit():
            tech_id = int(submitted_technician)
            # 0 means unassign, set to None
            ticket.technician_id = tech_id if tech_id > 0 else None

        if ticket.first_response_at is None and ticket.status in ('En proceso', 'Esperando usuario', 'Cerrado'):
            ticket.first_response_at = datetime.utcnow()

        if previous_status == 'Cerrado' and ticket.status != 'Cerrado':
            ticket.reopened_count = (ticket.reopened_count or 0) + 1

        if ticket.status == 'Cerrado':
            ticket.resolved_at = datetime.utcnow()
        elif ticket.resolved_at is not None:
            ticket.resolved_at = None

        db.session.commit()
        flash(
            _t('Ticket #{id} updated successfully - Status: {status}').format(
                id=ticket.id,
                status=ticket.status,
            ),
            'success'
        )
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    # prefill form
    form.status.data = ticket.status
    form.technician.data = ticket.technician_id or 0
    comments = ticket.comments.order_by(TicketComment.created_at.asc()).all()
    attachments = ticket.attachments.order_by(TicketAttachment.created_at.desc()).all()
    return render_template('tickets/detail.html', ticket=ticket, form=form, comment_form=comment_form,
                           comments=comments, attachments=attachments)
