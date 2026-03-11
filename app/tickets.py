import os
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, current_app, session, send_from_directory, abort, jsonify
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from sqlalchemy import and_, case
from werkzeug.utils import secure_filename

from app import db, translate, socketio
from app.models import Ticket, User, TicketComment, TicketAttachment
from app.forms import TicketForm, TicketUpdateForm, TicketCommentForm, CSATForm
from app.security import AuditHelper

bp = Blueprint('tickets', __name__)


def _t(text):
    return translate(text, session.get('lang', 'en'))


def _ticket_read_access(ticket):
    return current_user.is_admin() or current_user.is_technician() or ticket.user_id == current_user.id


def _ticket_chat_access(ticket):
    return (
        current_user.is_admin()
        or ticket.user_id == current_user.id
        or (current_user.is_technician() and ticket.technician_id == current_user.id)
    )


def _serialize_comment(ticket, comment):
    user_role = comment.user.role if comment.user else 'user'
    message_role = 'admin'
    if comment.user_id == ticket.user_id:
        message_role = 'client'
    elif ticket.technician_id and comment.user_id == ticket.technician_id:
        message_role = 'technician'

    return {
        'id': comment.id,
        'username': comment.user.username if comment.user else _t('User'),
        'user_role': user_role,
        'message_role': message_role,
        'message': comment.message,
        'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
    }


def _safe_datetime_text(value, fmt='%Y-%m-%d %H:%M'):
    return value.strftime(fmt) if hasattr(value, 'strftime') else None


@socketio.on('connect')
def handle_connect():
    """Register user as online when they connect"""
    from flask import current_app
    from app import online_users
    
    current_app.logger.info(f'=== Socket.IO Connect Event ===')
    current_app.logger.info(f'is_authenticated: {current_user.is_authenticated}')
    current_app.logger.info(f'Online users dict before: {online_users}')
    
    if current_user.is_authenticated:
        user_id = current_user.id
        username = current_user.username
        user_role = current_user.role
        
        # Register user
        online_users[user_id] = {
            'username': username,
            'user_role': user_role,
            'joined_at': datetime.utcnow(),
        }
        
        current_app.logger.info(f'✅ User registered: {username} (ID: {user_id}, Role: {user_role})')
        current_app.logger.info(f'Online users dict after: {online_users}')
        current_app.logger.info(f'Total online: {len(online_users)}')
        
        # Emit confirmation to client
        emit('user_registered', {
            'user_id': user_id,
            'username': username,
            'total_online': len(online_users)
        })
    else:
        current_app.logger.warning('⚠️ Connect attempt but user NOT authenticated')
        current_app.logger.info(f'Current user: {current_user}')
        current_app.logger.info(f'Current user is_authenticated: {getattr(current_user, "is_authenticated", "NO ATTRIBUTE")}')


@socketio.on('join_ticket_room')
def handle_join_ticket_room(data):
    ticket_id = (data or {}).get('ticket_id')
    if not ticket_id:
        emit('chat_error', {'error': 'missing_ticket_id'})
        return

    ticket = Ticket.query.get(ticket_id)
    if not ticket or not _ticket_read_access(ticket):
        emit('chat_error', {'error': 'forbidden'})
        return

    join_room(f'ticket_{ticket.id}')
    emit('user_online', {
        'ticket_id': ticket.id,
        'user_id': current_user.id,
        'username': current_user.username,
        'user_role': current_user.role,
    }, room=f'ticket_{ticket.id}')
    emit('chat_joined', {'ticket_id': ticket.id})


@socketio.on('disconnect')
def handle_disconnect():
    """Remove user from online registry when they disconnect"""
    from flask import current_app
    
    if current_user.is_authenticated:
        from app import online_users
        username = current_user.username
        user_id = current_user.id
        online_users.pop(user_id, None)
        current_app.logger.info(f'User {username} (ID: {user_id}) disconnected. Total online: {len(online_users)}')
        
        emit('user_offline', {
            'user_id': user_id,
            'username': username,
        }, broadcast=True)
    else:
        current_app.logger.warning('Socket.IO disconnect but user not authenticated')


@socketio.on('ticket_chat_message')
def handle_ticket_chat_message(data):
    ticket_id = (data or {}).get('ticket_id')
    message = ((data or {}).get('message') or '').strip()
    if not ticket_id or not message:
        emit('chat_error', {'error': 'invalid_payload'})
        return

    ticket = Ticket.query.get(ticket_id)
    if not ticket or not _ticket_chat_access(ticket):
        emit('chat_error', {'error': 'forbidden'})
        return

    comment = TicketComment(ticket_id=ticket.id, user_id=current_user.id, message=message)
    db.session.add(comment)
    db.session.commit()
    payload = _serialize_comment(ticket, comment)
    emit('ticket_chat_message', payload, room=f'ticket_{ticket.id}')


def _attachments_dir():
    # In Render, use persistent storage at /mnt/data
    # In development, use instance/uploads
    if os.environ.get('RENDER') == 'true':
        upload_dir = '/mnt/data/uploads'
    else:
        upload_dir = os.path.join(current_app.instance_path, 'uploads')
    
    try:
        os.makedirs(upload_dir, exist_ok=True)
    except (OSError, PermissionError) as e:
        # If persistent storage unavailable, fallback to instance dir
        current_app.logger.warning(f'Failed to create upload dir {upload_dir}: {e}. Using instance directory.')
        upload_dir = os.path.join(current_app.instance_path, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
    
    return upload_dir


def _save_attachment(file_storage, ticket_id):
    if not file_storage or not file_storage.filename:
        return None

    # Security: Validate file
    from app.security import FileSecurityValidator
    is_valid, error_msg, mime_type = FileSecurityValidator.validate(file_storage)
    if not is_valid:
        current_app.logger.warning(f'File upload validation failed: {error_msg}')
        return None

    original_filename = secure_filename(file_storage.filename)
    if not original_filename:
        return None

    ext = os.path.splitext(original_filename)[1]
    stored_filename = f"ticket_{ticket_id}_{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(_attachments_dir(), stored_filename)
    
    # Save file
    try:
        file_storage.save(full_path)
    except Exception as e:
        current_app.logger.error(f'Failed to save attachment: {e}')
        return None
    
    # Security: Scan for malware patterns
    is_safe, scan_msg = FileSecurityValidator.scan_for_malware(full_path)
    if not is_safe:
        # Delete file if malware detected
        try:
            os.remove(full_path)
        except:
            pass
        current_app.logger.warning(f'Malware scan failed: {scan_msg}')
        return None

    size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
    attachment = TicketAttachment(
        ticket_id=ticket_id,
        uploaded_by_id=current_user.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=mime_type or file_storage.content_type,
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

        now = datetime.utcnow()
        closed_rank = case((Ticket.status == 'Cerrado', 1), else_=0)
        overdue_rank = case(
            (and_(Ticket.sla_due_at.is_not(None), Ticket.status != 'Cerrado', Ticket.sla_due_at < now), 0),
            else_=1,
        )
        missing_sla_rank = case((Ticket.sla_due_at.is_(None), 1), else_=0)

        ticket_records = q.order_by(
            closed_rank.asc(),
            overdue_rank.asc(),
            missing_sla_rank.asc(),
            Ticket.sla_due_at.asc(),
            Ticket.created_at.desc(),
        ).all()

        tickets = []
        skipped_records = 0
        for ticket in ticket_records:
            try:
                is_closed = ticket.status == 'Cerrado'
                try:
                    is_overdue = ticket.is_overdue()
                except Exception:
                    is_overdue = False
                try:
                    is_due_soon = ticket.is_due_soon()
                except Exception:
                    is_due_soon = False

                tickets.append({
                    'id': ticket.id,
                    'title': ticket.title or '—',
                    'description': ticket.description or '',
                    'status': ticket.status or '',
                    'priority': ticket.priority or '',
                    'category': ticket.category or '',
                    'creator_name': ticket.creator_name or '—',
                    'created_at_text': _safe_datetime_text(ticket.created_at, '%Y-%m-%d') or '—',
                    'sla_due_at_text': _safe_datetime_text(ticket.sla_due_at) or '—',
                    'sla_state': 'closed' if is_closed else 'overdue' if is_overdue else 'due_soon' if is_due_soon else 'on_time' if ticket.sla_due_at else 'none',
                })
            except Exception:
                skipped_records += 1
                current_app.logger.exception('Skipping malformed ticket row id=%s during list rendering', getattr(ticket, 'id', None))

        if skipped_records:
            flash(_t('Some historical ticket records could not be rendered and were skipped.'), 'warning')

        # Get categories and priorities safely
        categories = Ticket.categories()
        priorities = Ticket.priorities()

        return render_template('tickets/list.html', tickets=tickets,
                               status=status, category=category, priority=priority,
                               start_date=start_date, end_date=end_date, keyword=keyword,
                               categories=categories, priorities=priorities)
    except Exception as e:
        current_app.logger.exception('Error rendering tickets list: %s', e)
        flash(_t('There was a problem loading the ticket list. Review historical records or contact admin.'), 'warning')
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
    if not _ticket_read_access(ticket):
        flash(_t('You do not have access to this ticket'), 'danger')
        return redirect(url_for('tickets.list_tickets'))

    # Direct chat permissions: owner, assigned technician, or admin.
    can_chat = _ticket_chat_access(ticket)

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
        if not can_chat:
            flash(_t('Only the requester, assigned technician, or admin can chat on this ticket'), 'danger')
            return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))
        comment = TicketComment(ticket_id=ticket.id, user_id=current_user.id, message=comment_form.message.data.strip())
        db.session.add(comment)
        db.session.commit()
        socketio.emit('ticket_chat_message', _serialize_comment(ticket, comment), room=f'ticket_{ticket.id}')
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
    csat_form = CSATForm(prefix='csat')
    return render_template('tickets/detail.html', ticket=ticket, form=form, comment_form=comment_form,
                           comments=comments, attachments=attachments, can_chat=can_chat,
                           csat_form=csat_form)


@bp.route('/<int:ticket_id>/csat', methods=['POST'])
@login_required
def submit_csat(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if ticket.user_id != current_user.id:
        abort(403)
    if ticket.status != 'Cerrado':
        flash(_t('You can only rate closed tickets'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))
    if ticket.satisfaction_rating:
        flash(_t('You have already submitted a rating for this ticket'), 'info')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))
    form = CSATForm(prefix='csat')
    if form.validate_on_submit():
        try:
            rating = int(form.rating.data)
        except (TypeError, ValueError):
            rating = None
        if not rating or rating < 1 or rating > 5:
            flash(_t('Please select a valid rating'), 'warning')
            return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))
        ticket.satisfaction_rating = rating
        db.session.commit()
        flash(_t('Thank you for your feedback!'), 'success')
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))


@bp.route('/<int:ticket_id>/chat-feed')
@login_required
def ticket_chat_feed(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not _ticket_read_access(ticket):
        return jsonify({'error': 'forbidden'}), 403

    comments = ticket.comments.order_by(TicketComment.created_at.asc()).all()
    payload = [_serialize_comment(ticket, c) for c in comments]

    return jsonify({'comments': payload})


@bp.route('/<int:ticket_id>/delete', methods=['POST'])
@login_required
def delete_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if current_user.is_admin():
        AuditHelper.log_ticket_action(current_user.id, 'delete_blocked', ticket.id)
    else:
        AuditHelper.log_ticket_action(current_user.id, 'delete_unauthorized', ticket.id)

    flash(_t('Ticket deletion is disabled by security policy'), 'warning')
    return redirect(url_for('tickets.list_tickets'))
