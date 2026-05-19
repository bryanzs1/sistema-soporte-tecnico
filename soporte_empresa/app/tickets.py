import os
import json
import uuid
import unicodedata
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, current_app, session, send_from_directory, abort, jsonify
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from sqlalchemy import and_, case, or_, func
from werkzeug.utils import secure_filename

from soporte_empresa.app import db, translate, socketio
from soporte_empresa.app.models import Ticket, User, TicketComment, TicketAttachment, AuditLog, KBArticle, TicketOption
from soporte_empresa.app.forms import TicketForm, TicketUpdateForm, TicketCommentForm, CSATForm
from soporte_empresa.app.security import AuditHelper

bp = Blueprint('tickets', __name__)

_chat_translation_cache = {}
_CHAT_TRANSLATION_CACHE_LIMIT = 2000


def utcnow():
    """Return naive UTC datetime for compatibility with current schema."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _t(text):
    return translate(text, session.get('lang', 'es'))


def _company_ticket_query():
    if current_user.is_authenticated and (current_user.is_admin() or current_user.is_technician()):
        return Ticket.query.filter(Ticket.company_id == current_user.company_id)
    return Ticket.query.filter_by(user_id=current_user.id)


def _company_ticket_or_404(ticket_id):
    return _company_ticket_query().filter(Ticket.id == ticket_id).first_or_404()


def _is_same_company_ticket(ticket):
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin() or current_user.is_technician():
        return ticket.company_id == current_user.company_id
    return ticket.user_id == current_user.id


def _translate_chat_free_text(message, target_lang):
    """Translate free-text chat content using external API when configured."""
    text = (message or '').strip()
    if not text:
        return message
    if target_lang not in ('en', 'es'):
        return message

    cache_key = f'{target_lang}:{text}'
    cached = _chat_translation_cache.get(cache_key)
    if cached:
        return cached

    api_url = current_app.config.get('CHAT_TRANSLATE_API_URL')
    if not api_url:
        return message

    endpoint = api_url.rstrip('/')
    if not endpoint.endswith('/translate'):
        endpoint = endpoint + '/translate'

    payload = {
        'q': text,
        'source': 'auto',
        'target': target_lang,
        'format': 'text',
    }
    api_key = current_app.config.get('CHAT_TRANSLATE_API_KEY')
    if api_key:
        payload['api_key'] = api_key

    try:
        import requests
        timeout = current_app.config.get('CHAT_TRANSLATE_TIMEOUT', 2.5)
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        if resp.ok:
            data = resp.json() if resp.content else {}
            translated = (data.get('translatedText') or '').strip()
            if translated:
                if len(_chat_translation_cache) >= _CHAT_TRANSLATION_CACHE_LIMIT:
                    # Remove the oldest inserted key in a simple FIFO manner.
                    first_key = next(iter(_chat_translation_cache))
                    _chat_translation_cache.pop(first_key, None)
                _chat_translation_cache[cache_key] = translated
                return translated
    except Exception as e:
        current_app.logger.debug('Chat translation failed: %s', e)

    return message


def _ticket_read_access(ticket):
    if current_user.is_admin() or current_user.is_technician():
        return _is_same_company_ticket(ticket)
    return ticket.user_id == current_user.id


def _ticket_chat_access(ticket):
    return (
        (current_user.is_admin() and _is_same_company_ticket(ticket))
        or ticket.user_id == current_user.id
        or (current_user.is_technician() and _is_same_company_ticket(ticket) and ticket.technician_id == current_user.id)
    )


def _technician_reassign_enabled():
    policy = TicketOption.query.filter_by(option_type='system_policy', value='technician_reassign').first()
    return bool(policy and policy.active)


def _is_technician_certification_active(technician):
    if not technician or not technician.certified_technician:
        return False
    if technician.certified_until and technician.certified_until < utcnow():
        technician.certified_technician = False
        return False
    return True


def _technician_matches_category(technician, category):
    category_norm = _strip_accents(category).lower()
    if not category_norm:
        return True
    specialties_norm = _strip_accents(technician.technician_specialties or '').lower()
    # Backward compatibility: legacy technicians without specialties remain eligible.
    if not specialties_norm:
        return True
    if category_norm in specialties_norm:
        return True
    keywords = [part for part in category_norm.split() if len(part) > 3]
    return any(keyword in specialties_norm for keyword in keywords)


def _normalize_filter_value(raw_value, allowed_values):
    """Normalize filter values so ES/EN inputs match stored canonical DB values."""
    value = (raw_value or '').strip()
    if not value:
        return None

    canonical_values = [v for v in (allowed_values or []) if v]
    if value in canonical_values:
        return value

    canonical_by_lower = {v.lower(): v for v in canonical_values}
    direct = canonical_by_lower.get(value.lower())
    if direct:
        return direct

    candidates = {value, value.title()}
    for candidate in candidates:
        for lang in ('es', 'en'):
            translated = translate(candidate, lang)
            if translated in canonical_values:
                return translated
            mapped = canonical_by_lower.get((translated or '').lower())
            if mapped:
                return mapped

    return value


def _keyword_variants(keyword):
    """Build a small set of language variants so keyword search works in ES and EN."""
    base = (keyword or '').strip()
    if not base:
        return []

    variants = {base}
    for candidate in (base, base.lower(), base.title()):
        for lang in ('es', 'en'):
            translated = translate(candidate, lang)
            if translated:
                variants.add(translated)

    return [v for v in variants if v]


def _strip_accents(text):
    """Return ASCII-like representation to make searches accent-insensitive."""
    source = (text or '').strip()
    if not source:
        return ''
    normalized = unicodedata.normalize('NFKD', source)
    return ''.join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_text_expr(expr):
    """Normalize SQL text expression for accent-insensitive matching across DB engines."""
    lowered = func.lower(expr)
    lowered = func.replace(lowered, 'á', 'a')
    lowered = func.replace(lowered, 'à', 'a')
    lowered = func.replace(lowered, 'ä', 'a')
    lowered = func.replace(lowered, 'â', 'a')
    lowered = func.replace(lowered, 'é', 'e')
    lowered = func.replace(lowered, 'è', 'e')
    lowered = func.replace(lowered, 'ë', 'e')
    lowered = func.replace(lowered, 'ê', 'e')
    lowered = func.replace(lowered, 'í', 'i')
    lowered = func.replace(lowered, 'ì', 'i')
    lowered = func.replace(lowered, 'ï', 'i')
    lowered = func.replace(lowered, 'î', 'i')
    lowered = func.replace(lowered, 'ó', 'o')
    lowered = func.replace(lowered, 'ò', 'o')
    lowered = func.replace(lowered, 'ö', 'o')
    lowered = func.replace(lowered, 'ô', 'o')
    lowered = func.replace(lowered, 'ú', 'u')
    lowered = func.replace(lowered, 'ù', 'u')
    lowered = func.replace(lowered, 'ü', 'u')
    lowered = func.replace(lowered, 'û', 'u')
    lowered = func.replace(lowered, 'ñ', 'n')
    return lowered


def _apply_keyword_filter(query, keyword):
    terms = _keyword_variants(keyword)
    if not terms:
        return query

    normalized_columns = [
        _normalize_text_expr(Ticket.title),
        _normalize_text_expr(Ticket.description),
        _normalize_text_expr(Ticket.status),
        _normalize_text_expr(Ticket.priority),
        _normalize_text_expr(Ticket.category),
    ]

    clauses = []
    for term in terms:
        normalized_term = _strip_accents(term).lower()
        if not normalized_term:
            continue
        kw = f"%{normalized_term}%"
        clauses.extend([column.like(kw) for column in normalized_columns])

    if not clauses:
        return query

    return query.filter(or_(*clauses))


def _localized_catalog_label(value, canonical_defaults):
    """Return a localized label for catalog values while preserving stored filter value."""
    raw = (value or '').strip()
    if not raw:
        return value

    # Direct translation first.
    direct = _t(raw)
    if direct != raw:
        return direct

    # Try common case variants because translation map is case-sensitive.
    for candidate in (raw.title(), raw.capitalize(), raw.lower(), raw.upper()):
        translated = _t(candidate)
        if translated != candidate:
            return translated

    # Normalize known defaults (ES/EN aliases) and translate from canonical value.
    canonical = _normalize_filter_value(raw, canonical_defaults)
    canonical_translated = _t(canonical)
    if canonical_translated != canonical:
        return canonical_translated
    return canonical


def _serialize_comment(ticket, comment):
    user_role = comment.user.role if comment.user else 'user'
    message_role = 'admin'
    if comment.user_id == ticket.user_id:
        message_role = 'client'
    elif ticket.technician_id and comment.user_id == ticket.technician_id:
        message_role = 'technician'

    target_lang = session.get('lang', 'es')
    translated_message = _t(comment.message)
    if translated_message == comment.message:
        translated_message = _translate_chat_free_text(comment.message, target_lang)

    return {
        'id': comment.id,
        'username': comment.user.username if comment.user else _t('User'),
        'user_role': user_role,
        'message_role': message_role,
        'message': translated_message,
        'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
    }


def _safe_datetime_text(value, fmt='%Y-%m-%d %H:%M'):
    return value.strftime(fmt) if hasattr(value, 'strftime') else None


def _sanitize_ticket_table_layout(payload):
    allowed_cols = {'id', 'title', 'status', 'priority', 'category', 'creator', 'sla-due', 'sla', 'action'}
    order = payload.get('order') if isinstance(payload, dict) else None
    hidden = payload.get('hidden') if isinstance(payload, dict) else None

    if not isinstance(order, list) or not isinstance(hidden, list):
        return None

    cleaned_order = []
    for item in order:
        if isinstance(item, str) and item in allowed_cols and item not in cleaned_order:
            cleaned_order.append(item)

    # Always keep all known columns in deterministic order.
    for col in ['id', 'title', 'status', 'priority', 'category', 'creator', 'sla-due', 'sla', 'action']:
        if col not in cleaned_order:
            cleaned_order.append(col)

    cleaned_hidden = []
    for item in hidden:
        if isinstance(item, str) and item in allowed_cols and item not in cleaned_hidden:
            cleaned_hidden.append(item)

    return {'order': cleaned_order, 'hidden': cleaned_hidden}


def _ticket_timeline(ticket):
    events = []
    if ticket.created_at:
        events.append({
            'at': ticket.created_at,
            'title': _t('Created'),
            'detail': _t('Ticket created by {name}').format(name=ticket.creator_name or _t('User')),
        })

    if ticket.first_response_at:
        events.append({
            'at': ticket.first_response_at,
            'title': _t('First response'),
            'detail': _t('Support team started working on the ticket'),
        })

    if ticket.resolved_at:
        events.append({
            'at': ticket.resolved_at,
            'title': _t('Resolved'),
            'detail': _t('Ticket marked as closed'),
        })

    if (ticket.reopened_count or 0) > 0:
        events.append({
            'at': ticket.updated_at or ticket.created_at,
            'title': _t('Reopened'),
            'detail': _t('This ticket was reopened {count} time(s)').format(count=ticket.reopened_count or 0),
        })

    events.sort(key=lambda x: x['at'] or utcnow())
    return events


def _reopen_deadline(ticket):
    if ticket.status != 'Cerrado':
        return None
    reference = ticket.resolved_at or ticket.updated_at or ticket.created_at
    if not reference:
        return None
    return reference + timedelta(days=7)


def _can_reopen_ticket(ticket):
    deadline = _reopen_deadline(ticket)
    if not deadline:
        return False
    return utcnow() <= deadline


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
            'joined_at': utcnow(),
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

    ticket = db.session.get(Ticket, ticket_id)
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

    ticket = db.session.get(Ticket, ticket_id)
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
        base_query = _company_ticket_query()

        # apply filters from query string
        view = request.args.get('view', type=str) or 'active'
        if view not in ('active', 'history', 'all'):
            view = 'active'
        raw_status = request.args.get('status', type=str)
        raw_category = request.args.get('category', type=str)
        raw_priority = request.args.get('priority', type=str)
        start_date = request.args.get('start_date', type=str)
        end_date = request.args.get('end_date', type=str)
        keyword = request.args.get('keyword', type=str)

        categories = Ticket.categories()
        priorities = Ticket.priorities()
        status = _normalize_filter_value(raw_status, Ticket.statuses())
        category = _normalize_filter_value(raw_category, categories)
        priority = _normalize_filter_value(raw_priority, priorities)

        filtered_query = base_query

        if status:
            filtered_query = filtered_query.filter_by(status=status)
        if category:
            filtered_query = filtered_query.filter_by(category=category)
        if priority:
            filtered_query = filtered_query.filter_by(priority=priority)
        if start_date:
            try:
                sd = datetime.fromisoformat(start_date)
                filtered_query = filtered_query.filter(Ticket.created_at >= sd)
            except ValueError:
                pass
        if end_date:
            try:
                ed = datetime.fromisoformat(end_date)
                filtered_query = filtered_query.filter(Ticket.created_at <= ed)
            except ValueError:
                pass
        filtered_query = _apply_keyword_filter(filtered_query, keyword)

        ticket_counts = {
            'active': filtered_query.filter(Ticket.status != 'Cerrado').count(),
            'history': filtered_query.filter(Ticket.status == 'Cerrado').count(),
        }
        ticket_counts['all'] = filtered_query.count()

        q = filtered_query

        if not status and view == 'active':
            q = q.filter(Ticket.status != 'Cerrado')
        elif not status and view == 'history':
            q = q.filter(Ticket.status == 'Cerrado')

        now = utcnow()
        closed_rank = case((Ticket.status == 'Cerrado', 1), else_=0)
        overdue_rank = case(
            (and_(Ticket.sla_due_at.isnot(None), Ticket.status != 'Cerrado', Ticket.sla_due_at < now), 0),
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
                    'technician_id': ticket.technician_id,
                    'created_at_text': _safe_datetime_text(ticket.created_at, '%Y-%m-%d') or '—',
                    'sla_due_at_text': _safe_datetime_text(ticket.sla_due_at) or '—',
                    'sla_state': 'closed' if is_closed else 'overdue' if is_overdue else 'due_soon' if is_due_soon else 'on_time' if ticket.sla_due_at else 'none',
                })
            except Exception:
                skipped_records += 1
                current_app.logger.exception('Skipping malformed ticket row id=%s during list rendering', getattr(ticket, 'id', None))

        if skipped_records:
            flash(_t('Some historical ticket records could not be rendered and were skipped.'), 'warning')

        category_labels = {
            c: _localized_catalog_label(c, Ticket.default_categories())
            for c in categories
        }
        priority_labels = {
            p: _localized_catalog_label(p, Ticket.default_priorities())
            for p in priorities
        }

        return render_template('tickets/list.html', tickets=tickets,
                               ticket_counts=ticket_counts,
                               view=view,
                               status=status, category=category, priority=priority,
                               start_date=start_date, end_date=end_date, keyword=keyword,
                               categories=categories, priorities=priorities,
                               category_labels=category_labels, priority_labels=priority_labels)
    except Exception as e:
        current_app.logger.exception('Error rendering tickets list: %s', e)
        try:
            AuditLog.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                action='ticket_list_query_error',
                resource_type='ticket',
                ip_address=AuditHelper.get_client_ip(),
                user_agent=AuditHelper.get_user_agent(),
                status='failure',
                details=json.dumps({
                    'error': str(e),
                    'status': request.args.get('status'),
                    'category': request.args.get('category'),
                    'priority': request.args.get('priority'),
                    'keyword': request.args.get('keyword'),
                })[:2000],
            )
        except Exception:
            current_app.logger.exception('Failed to write audit log for ticket_list_query_error')
        try:
            fallback_query = _company_ticket_query()

            fallback_records = fallback_query.order_by(Ticket.id.desc()).limit(500).all()
            fallback_tickets = []
            for ticket in fallback_records:
                fallback_tickets.append({
                    'id': ticket.id,
                    'title': ticket.title or '—',
                    'description': ticket.description or '',
                    'status': ticket.status or '',
                    'priority': ticket.priority or '',
                    'category': ticket.category or '',
                    'creator_name': ticket.creator_name or '—',
                    'technician_id': ticket.technician_id,
                    'created_at_text': _safe_datetime_text(ticket.created_at, '%Y-%m-%d') or '—',
                    'sla_due_at_text': _safe_datetime_text(ticket.sla_due_at) or '—',
                    'sla_state': 'none',
                })

            return render_template('tickets/list.html', tickets=fallback_tickets,
                                   ticket_counts=ticket_counts,
                                   view=view,
                                   status=None, category=None, priority=None,
                                   start_date=None, end_date=None, keyword=None,
                                   categories=Ticket.default_categories(),
                                   priorities=Ticket.default_priorities(),
                                   category_labels={
                                       c: _localized_catalog_label(c, Ticket.default_categories())
                                       for c in Ticket.default_categories()
                                   },
                                   priority_labels={
                                       p: _localized_catalog_label(p, Ticket.default_priorities())
                                       for p in Ticket.default_priorities()
                                   })
        except Exception:
            current_app.logger.exception('Fallback ticket list query also failed')
            flash(_t('There was a problem loading the ticket list. Review historical records or contact admin.'), 'warning')
            try:
                AuditLog.log_action(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    action='ticket_list_fallback_error',
                    resource_type='ticket',
                    ip_address=AuditHelper.get_client_ip(),
                    user_agent=AuditHelper.get_user_agent(),
                    status='failure',
                    details='fallback_query_failed',
                )
            except Exception:
                current_app.logger.exception('Failed to write audit log for ticket_list_fallback_error')
            return render_template('tickets/list.html', tickets=[],
                                   ticket_counts=ticket_counts,
                                   view=view,
                                   status=None, category=None, priority=None,
                                   start_date=None, end_date=None, keyword=None,
                                   categories=Ticket.default_categories(),
                                   priorities=Ticket.default_priorities())


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    form = TicketForm()
    form.creator_name.data = current_user.username
    if request.method == 'GET':
        requested_title = (request.args.get('title') or '').strip()
        requested_description = (request.args.get('description') or '').strip()
        requested_category = (request.args.get('category') or '').strip()
        valid_categories = {value for value, _label in form.category.choices}

        if requested_title and not form.title.data:
            form.title.data = requested_title[:140]
        if requested_description and not form.description.data:
            form.description.data = requested_description
        if requested_category in valid_categories:
            form.category.data = requested_category

    if form.validate_on_submit():
        ticket = Ticket(
            title=form.title.data,
            # Always persist authenticated username as ticket creator.
            creator_name=current_user.username,
            description=form.description.data,
            category=form.category.data,
            priority=form.priority.data,
            user=current_user,
            company_id=current_user.company_id,
        )
        ticket.sla_due_at = utcnow() + timedelta(hours=Ticket.sla_hours_by_priority(ticket.priority))
        
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
                suggested_technician = User.query.filter(
                    User.id == suggested_tech_id,
                    User.role == 'technician',
                    User.certified_technician == True,
                    User.company_id == ticket.company_id,
                ).first()
                if suggested_technician and _is_technician_certification_active(suggested_technician) and _technician_matches_category(suggested_technician, ticket.category):
                    ticket.ml_suggested_technician_id = suggested_technician.id
                    ticket.ml_confidence_score = confidence

                    # Auto-asignar si la confianza es muy alta (>70%)
                    if confidence > 0.7:
                        ticket.technician_id = suggested_technician.id
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


@bp.route('/kb-suggestions')
@login_required
def kb_suggestions():
    query = request.args.get('q', '').strip()
    if len(query) < 3:
        return jsonify([])

    like = f'%{query}%'
    found = KBArticle.query.join(User, KBArticle.created_by_id == User.id).filter(
        KBArticle.is_active.is_(True),
        User.company_id == current_user.company_id,
    ).filter(
        (KBArticle.title.ilike(like)) | (KBArticle.content.ilike(like))
    ).order_by(KBArticle.updated_at.desc()).limit(6).all()

    return jsonify([
        {
            'id': article.id,
            'title': article.title,
            'preview': article.content[:180] + ('...' if len(article.content) > 180 else ''),
        }
        for article in found
    ])


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
        company_id=current_user.company_id,
    )
    ticket.sla_due_at = utcnow() + timedelta(hours=Ticket.sla_hours_by_priority(ticket.priority))
    
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
            suggested_technician = User.query.filter(
                User.id == suggested_tech_id,
                User.role == 'technician',
                User.company_id == ticket.company_id,
            ).first()
            if suggested_technician:
                ticket.ml_suggested_technician_id = suggested_technician.id
                ticket.ml_confidence_score = confidence

                # Auto-asignar si la confianza es muy alta (>70%)
                if confidence > 0.7:
                    ticket.technician_id = suggested_technician.id
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
    allowed = _ticket_read_access(ticket)
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
    q = _company_ticket_query()
    view = request.args.get('view', type=str) or 'active'
    if view not in ('active', 'history', 'all'):
        view = 'active'
    raw_status = request.args.get('status', type=str)
    raw_category = request.args.get('category', type=str)
    raw_priority = request.args.get('priority', type=str)
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    keyword = request.args.get('keyword', type=str)
    fmt = request.args.get('format', 'csv')  # csv or xlsx
    # common imports
    import io

    status = _normalize_filter_value(raw_status, Ticket.statuses())
    category = _normalize_filter_value(raw_category, Ticket.categories())
    priority = _normalize_filter_value(raw_priority, Ticket.priorities())

    if status:
        q = q.filter_by(status=status)
    elif view == 'active':
        q = q.filter(Ticket.status != 'Cerrado')
    elif view == 'history':
        q = q.filter(Ticket.status == 'Cerrado')
    if category:
        q = q.filter_by(category=category)
    if priority:
        q = q.filter_by(priority=priority)
    if start_date:
        try:
            sd = datetime.fromisoformat(start_date)
            q = q.filter(Ticket.created_at >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.fromisoformat(end_date)
            q = q.filter(Ticket.created_at <= ed)
        except ValueError:
            pass
    q = _apply_keyword_filter(q, keyword)
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
    ticket = _company_ticket_or_404(ticket_id)
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
        thirty_min_ago = utcnow() - timedelta(minutes=30)
        techs = User.query.filter(
            User.role == 'technician',
            User.is_active == True,
            User.certified_technician == True,
            User.last_activity >= thirty_min_ago,
            User.company_id == ticket.company_id,
        ).order_by(User.username).all()
        valid_techs = [t for t in techs if _is_technician_certification_active(t) and _technician_matches_category(t, ticket.category)]
        if len(valid_techs) != len(techs):
            db.session.commit()
        # Add "Unassigned" option first
        form.technician.choices = [(0, _t('-- Unassigned --'))] + [(t.id, f"{t.username} (online)") for t in valid_techs]
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
        can_reassign_technician = current_user.is_admin() or (current_user.is_technician() and _technician_reassign_enabled())
        if can_reassign_technician and submitted_technician and str(submitted_technician).isdigit():
            tech_id = int(submitted_technician)
            # 0 means unassign, set to None
            ticket.technician_id = tech_id if tech_id > 0 else None
        elif (not can_reassign_technician) and submitted_technician is not None:
            # Defense in depth: prevent forged requests from technicians changing assignment.
            flash(_t('Only administrators can assign or reassign technicians'), 'warning')

        if ticket.first_response_at is None and ticket.status in ('En proceso', 'Esperando usuario', 'Cerrado'):
            ticket.first_response_at = utcnow()

        if previous_status == 'Cerrado' and ticket.status != 'Cerrado':
            ticket.reopened_count = (ticket.reopened_count or 0) + 1

        if ticket.status == 'Cerrado':
            ticket.resolved_at = utcnow()
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
    timeline = _ticket_timeline(ticket)
    reopen_deadline = _reopen_deadline(ticket)
    can_reopen_window = _can_reopen_ticket(ticket)
    return render_template('tickets/detail.html', ticket=ticket, form=form, comment_form=comment_form,
                           comments=comments, attachments=attachments, can_chat=can_chat,
                           csat_form=csat_form, timeline=timeline,
                           reopen_deadline=reopen_deadline, can_reopen_window=can_reopen_window,
                           technician_reassign_enabled=_technician_reassign_enabled())


@bp.route('/<int:ticket_id>/take', methods=['POST'])
@login_required
def take_ticket(ticket_id):
    ticket = _company_ticket_or_404(ticket_id)

    if not current_user.is_technician() and not current_user.is_admin():
        abort(403)

    if current_user.is_technician() and not _is_technician_certification_active(current_user):
        db.session.commit()
        flash(_t('Your technician certification has expired. Please request recertification.'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    if current_user.is_technician() and not _technician_matches_category(current_user, ticket.category):
        flash(_t('This ticket category is outside your certified specialties.'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    if ticket.status == 'Cerrado':
        flash(_t('Closed tickets cannot be taken'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    if ticket.technician_id and ticket.technician_id != current_user.id:
        flash(_t('This ticket is already assigned to another technician'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    if ticket.technician_id == current_user.id:
        flash(_t('This ticket is already assigned to you'), 'info')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    ticket.technician_id = current_user.id
    if ticket.status == 'Abierto':
        ticket.status = 'En proceso'
    if ticket.first_response_at is None:
        ticket.first_response_at = utcnow()

    db.session.add(TicketComment(
        ticket_id=ticket.id,
        user_id=current_user.id,
        message=_t('Ticket taken by technician {username}').format(username=current_user.username),
    ))
    db.session.commit()

    flash(_t('You have taken ticket #{id} successfully').format(id=ticket.id), 'success')

    next_target = request.form.get('next')
    if next_target == 'list':
        return redirect(url_for('tickets.list_tickets'))
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))


@bp.route('/<int:ticket_id>/release', methods=['POST'])
@login_required
def release_ticket(ticket_id):
    ticket = _company_ticket_or_404(ticket_id)

    if not current_user.is_technician() and not current_user.is_admin():
        abort(403)

    if ticket.status == 'Cerrado':
        flash(_t('Closed tickets cannot be released'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    if not ticket.technician_id:
        flash(_t('This ticket is already unassigned'), 'info')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    if current_user.is_technician() and ticket.technician_id != current_user.id:
        flash(_t('You can only release tickets assigned to you'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    ticket.technician_id = None
    if ticket.status != 'Cerrado':
        ticket.status = 'Abierto'

    db.session.add(TicketComment(
        ticket_id=ticket.id,
        user_id=current_user.id,
        message=_t('Ticket released by {username} and returned to the unassigned queue').format(username=current_user.username),
    ))
    db.session.commit()

    flash(_t('Ticket #{id} was released successfully').format(id=ticket.id), 'success')

    next_target = request.form.get('next')
    if next_target == 'list':
        return redirect(url_for('tickets.list_tickets'))
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))


@bp.route('/<int:ticket_id>/reopen', methods=['POST'])
@login_required
def reopen_ticket(ticket_id):
    ticket = _company_ticket_or_404(ticket_id)
    can_reopen = current_user.is_admin() or current_user.is_technician() or ticket.user_id == current_user.id
    if not can_reopen:
        abort(403)

    if ticket.status != 'Cerrado':
        flash(_t('Only closed tickets can be reopened'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    if not _can_reopen_ticket(ticket):
        flash(_t('Reopen window expired. Closed tickets can only be reopened within 7 days.'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    reason = (request.form.get('reopen_reason') or '').strip()
    if len(reason) < 5:
        flash(_t('Please provide a short reason to reopen the ticket'), 'warning')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))

    ticket.status = 'Abierto'
    ticket.reopened_count = (ticket.reopened_count or 0) + 1
    ticket.resolved_at = None

    db.session.add(TicketComment(
        ticket_id=ticket.id,
        user_id=current_user.id,
        message=_t('Reopen reason: {reason}').format(reason=reason),
    ))
    db.session.commit()

    # Notify requester and assigned technician so both sides are aware of the reopen.
    recipients = []
    if ticket.user and ticket.user.email:
        recipients.append(ticket.user.email)
    if ticket.technician and ticket.technician.email:
        recipients.append(ticket.technician.email)
    recipients = sorted(set(recipients))

    if recipients:
        try:
            from app import send_email
            send_email(
                _t('Ticket reopened notification'),
                recipients,
                _t('Ticket #{id} was reopened by {user}. Reason: {reason}').format(
                    id=ticket.id,
                    user=current_user.username,
                    reason=reason,
                ),
            )
        except Exception:
            current_app.logger.exception('Failed to send reopen notification for ticket #%s', ticket.id)

    flash(_t('Ticket reopened successfully'), 'success')
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))


@bp.route('/<int:ticket_id>/csat', methods=['POST'])
@login_required
def submit_csat(ticket_id):
    ticket = _company_ticket_or_404(ticket_id)
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
    ticket = _company_ticket_or_404(ticket_id)
    if not _ticket_read_access(ticket):
        return jsonify({'error': 'forbidden'}), 403

    comments = ticket.comments.order_by(TicketComment.created_at.asc()).all()
    payload = [_serialize_comment(ticket, c) for c in comments]

    return jsonify({'comments': payload})


@bp.route('/<int:ticket_id>/delete', methods=['POST'])
@login_required
def delete_ticket(ticket_id):
    ticket = _company_ticket_or_404(ticket_id)
    if current_user.is_admin():
        AuditHelper.log_ticket_action(current_user.id, 'delete_blocked', ticket.id)
    else:
        AuditHelper.log_ticket_action(current_user.id, 'delete_unauthorized', ticket.id)

    flash(_t('Ticket deletion is disabled by security policy'), 'warning')
    return redirect(url_for('tickets.list_tickets'))
