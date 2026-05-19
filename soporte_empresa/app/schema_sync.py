from sqlalchemy import inspect, text

from soporte_empresa.app import db


USER_COLUMNS = {
    'company_id': 'ALTER TABLE "user" ADD COLUMN company_id INTEGER',
    'certified_technician': 'ALTER TABLE "user" ADD COLUMN certified_technician BOOLEAN NOT NULL DEFAULT TRUE',
    'certified_until': 'ALTER TABLE "user" ADD COLUMN certified_until TIMESTAMP',
    'technician_specialties': 'ALTER TABLE "user" ADD COLUMN technician_specialties TEXT',
    'totp_secret': 'ALTER TABLE "user" ADD COLUMN totp_secret VARCHAR(32)',
    'totp_enabled': 'ALTER TABLE "user" ADD COLUMN totp_enabled BOOLEAN NOT NULL DEFAULT FALSE',
    'totp_backup_codes': 'ALTER TABLE "user" ADD COLUMN totp_backup_codes TEXT',
    'password_changed_at': 'ALTER TABLE "user" ADD COLUMN password_changed_at TIMESTAMP',
    'failed_login_attempts': 'ALTER TABLE "user" ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0',
    'last_failed_login_at': 'ALTER TABLE "user" ADD COLUMN last_failed_login_at TIMESTAMP',
    'locked_until': 'ALTER TABLE "user" ADD COLUMN locked_until TIMESTAMP',
}

TICKET_COLUMNS = {
    'company_id': 'ALTER TABLE ticket ADD COLUMN company_id INTEGER',
    'sla_due_at': 'ALTER TABLE ticket ADD COLUMN sla_due_at TIMESTAMP',
    'first_response_at': 'ALTER TABLE ticket ADD COLUMN first_response_at TIMESTAMP',
    'resolved_at': 'ALTER TABLE ticket ADD COLUMN resolved_at TIMESTAMP',
    'reopened_count': 'ALTER TABLE ticket ADD COLUMN reopened_count INTEGER NOT NULL DEFAULT 0',
    'resolution_time_minutes': 'ALTER TABLE ticket ADD COLUMN resolution_time_minutes INTEGER',
    'satisfaction_rating': 'ALTER TABLE ticket ADD COLUMN satisfaction_rating INTEGER',
    'ml_suggested_technician_id': 'ALTER TABLE ticket ADD COLUMN ml_suggested_technician_id INTEGER',
    'ml_confidence_score': 'ALTER TABLE ticket ADD COLUMN ml_confidence_score FLOAT',
    'auto_assigned': 'ALTER TABLE ticket ADD COLUMN auto_assigned BOOLEAN DEFAULT FALSE',
    'sentiment_label': 'ALTER TABLE ticket ADD COLUMN sentiment_label VARCHAR(20)',
    'sentiment_score': 'ALTER TABLE ticket ADD COLUMN sentiment_score FLOAT',
    'urgency_level': 'ALTER TABLE ticket ADD COLUMN urgency_level VARCHAR(20)',
    'ai_response': 'ALTER TABLE ticket ADD COLUMN ai_response TEXT',
    'ai_response_id': 'ALTER TABLE ticket ADD COLUMN ai_response_id INTEGER',
    'ai_response_confidence': 'ALTER TABLE ticket ADD COLUMN ai_response_confidence FLOAT',
    'ai_response_accepted': 'ALTER TABLE ticket ADD COLUMN ai_response_accepted BOOLEAN',
}

TICKET_ATTACHMENT_COLUMNS = {
    'uploaded_by_id': 'ALTER TABLE ticket_attachment ADD COLUMN uploaded_by_id INTEGER',
    'original_filename': 'ALTER TABLE ticket_attachment ADD COLUMN original_filename VARCHAR(255)',
}

TICKET_OPTION_COLUMNS = {
    'active': 'ALTER TABLE ticket_option ADD COLUMN active BOOLEAN NOT NULL DEFAULT TRUE',
    'created_at': 'ALTER TABLE ticket_option ADD COLUMN created_at TIMESTAMP',
}

API_TOKEN_COLUMNS = {
    'company_id': 'ALTER TABLE api_token ADD COLUMN company_id INTEGER',
}

INTEGRATION_COLUMNS = {
    'company_id': 'ALTER TABLE integration ADD COLUMN company_id INTEGER',
}

AUDIT_LOG_COLUMNS = {
    'company_id': 'ALTER TABLE audit_log ADD COLUMN company_id INTEGER',
}

COMPANY_COLUMNS = {
    'is_active': 'ALTER TABLE company ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE',
    'deactivation_reason': 'ALTER TABLE company ADD COLUMN deactivation_reason VARCHAR(255)',
}


def _ensure_columns(table_name, columns):
    inspector = inspect(db.engine)
    existing = {col['name'] for col in inspector.get_columns(table_name)}
    added = []
    for column_name, sql in columns.items():
        if column_name in existing:
            continue
        db.session.execute(text(sql))
        added.append(column_name)
    if added:
        db.session.commit()
    return added


def ensure_runtime_schema():
    """Idempotent schema sync for environments with drifted legacy databases."""
    from soporte_empresa.app import models  # noqa: F401

    db.create_all()

    changes = {}
    try:
        changes['user'] = _ensure_columns('user', USER_COLUMNS)
    except Exception:
        db.session.rollback()
        raise

    try:
        changes['ticket'] = _ensure_columns('ticket', TICKET_COLUMNS)
    except Exception:
        db.session.rollback()
        raise

    try:
        changes['ticket_attachment'] = _ensure_columns('ticket_attachment', TICKET_ATTACHMENT_COLUMNS)
    except Exception:
        db.session.rollback()
        # table may not exist yet in some legacy environments; create_all above should cover it
        raise

    try:
        changes['ticket_option'] = _ensure_columns('ticket_option', TICKET_OPTION_COLUMNS)
    except Exception:
        db.session.rollback()
        raise

    try:
        changes['api_token'] = _ensure_columns('api_token', API_TOKEN_COLUMNS)
    except Exception:
        db.session.rollback()
        raise

    try:
        changes['integration'] = _ensure_columns('integration', INTEGRATION_COLUMNS)
    except Exception:
        db.session.rollback()
        raise

    try:
        changes['audit_log'] = _ensure_columns('audit_log', AUDIT_LOG_COLUMNS)
    except Exception:
        db.session.rollback()
        raise

    try:
        changes['company'] = _ensure_columns('company', COMPANY_COLUMNS)
    except Exception:
        db.session.rollback()
        raise

    return changes
