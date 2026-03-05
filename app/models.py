from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError


roles = ('user', 'technician', 'admin')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Security: 2FA (TOTP)
    totp_secret = db.Column(db.String(32))  # Encrypted TOTP secret
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    totp_backup_codes = db.Column(db.Text)  # Comma-separated backup codes (encrypted)
    
    # Security: Password Management
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_failed_login_at = db.Column(db.DateTime)
    locked_until = db.Column(db.DateTime)  # Account locked until this time

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_technician(self):
        return self.role == 'technician'
    
    def is_account_locked(self):
        """Check if account is locked due to failed login attempts"""
        if self.locked_until is None:
            return False
        if datetime.utcnow() > self.locked_until:
            # Lock expired, reset attempts
            self.failed_login_attempts = 0
            self.locked_until = None
            db.session.commit()
            return False
        return True
    
    def record_failed_login(self):
        """Record a failed login attempt and lock account if needed"""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        self.last_failed_login_at = datetime.utcnow()
        
        # Lock account after 5 failed attempts for 15 minutes
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)
        
        db.session.commit()
    
    def reset_failed_login(self):
        """Reset failed login attempts on successful login"""
        self.failed_login_attempts = 0
        self.locked_until = None
        db.session.commit()


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    # nombre de la persona que crea el ticket (puede diferir del usuario de login)
    creator_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(64))
    priority = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Abierto')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sla_due_at = db.Column(db.DateTime)
    first_response_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    reopened_count = db.Column(db.Integer, default=0, nullable=False)
    
    # ML-related fields
    resolution_time_minutes = db.Column(db.Integer)  # tiempo real de resolucion
    satisfaction_rating = db.Column(db.Integer)  # 1-5 rating opcional
    ml_suggested_technician_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ml_confidence_score = db.Column(db.Float)  # 0-1 confianza del modelo
    auto_assigned = db.Column(db.Boolean, default=False)  # si fue asignado automaticamente

    ml_suggested_technician = db.relationship('User', foreign_keys=[ml_suggested_technician_id])

    # AI Sentiment Analysis fields
    sentiment_label = db.Column(db.String(20))  # 'very_negative', 'negative', 'neutral', 'positive', 'very_positive'
    sentiment_score = db.Column(db.Float)  # -1 to 1 sentiment polarity
    urgency_level = db.Column(db.String(20))  # 'high', 'medium', 'low'
    
    # AI Chatbot auto-response fields
    ai_response = db.Column(db.Text)  # Automatic response text (if any)
    ai_response_id = db.Column(db.Integer)  # KB entry ID that was used
    ai_response_confidence = db.Column(db.Float)  # 0-1 confidence in auto-response
    ai_response_accepted = db.Column(db.Boolean)  # Did user accept the auto-response?

    # possible values for dropdowns can be defined in code
    @staticmethod
    def default_categories():
        return ['Red', 'Impresoras', 'Software', 'Hardware']

    @staticmethod
    def default_priorities():
        return ['Baja', 'Media', 'Alta', 'Crítica']

    @staticmethod
    def categories():
        try:
            values = [
                item.value for item in TicketOption.query
                .filter_by(option_type='category', active=True)
                .order_by(TicketOption.value.asc())
                .all()
            ]
            return values or Ticket.default_categories()
        except SQLAlchemyError:
            return Ticket.default_categories()

    @staticmethod
    def priorities():
        try:
            values = [
                item.value for item in TicketOption.query
                .filter_by(option_type='priority', active=True)
                .order_by(TicketOption.value.asc())
                .all()
            ]
            return values or Ticket.default_priorities()
        except SQLAlchemyError:
            return Ticket.default_priorities()

    @staticmethod
    def statuses():
        return ['Abierto','En proceso','Esperando usuario','Cerrado']
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    technician_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    user = db.relationship('User', foreign_keys=[user_id], backref='tickets_created')
    technician = db.relationship('User', foreign_keys=[technician_id], backref='tickets_assigned')

    @staticmethod
    def sla_hours_by_priority(priority):
        mapping = {
            'Baja': 72,
            'Media': 24,
            'Alta': 8,
            'Crítica': 4,
        }
        return mapping.get(priority, 24)

    def is_closed(self):
        return self.status == 'Cerrado'

    def is_overdue(self):
        return bool(self.sla_due_at and not self.is_closed() and datetime.utcnow() > self.sla_due_at)


class TicketComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    ticket = db.relationship('Ticket', backref=db.backref('comments', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('ticket_comments', lazy='dynamic'))


class TicketAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False, index=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    content_type = db.Column(db.String(120))
    file_size = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    ticket = db.relationship('Ticket', backref=db.backref('attachments', lazy='dynamic', cascade='all, delete-orphan'))
    uploaded_by = db.relationship('User', backref=db.backref('ticket_attachments', lazy='dynamic'))


class TicketOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option_type = db.Column(db.String(20), nullable=False)  # category | priority
    value = db.Column(db.String(64), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('option_type', 'value', name='uq_ticket_option_type_value'),
    )

class TechnicianStats(db.Model):
    """Estadísticas de técnicos para el sistema ML"""
    id = db.Column(db.Integer, primary_key=True)
    technician_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    total_tickets_resolved = db.Column(db.Integer, default=0)
    avg_resolution_time = db.Column(db.Float)  # en minutos
    avg_satisfaction = db.Column(db.Float)  # promedio de ratings
    specialization = db.Column(db.String(200))  # categorías donde es experto (JSON)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    technician = db.relationship('User', backref=db.backref('stats', uselist=False))


class ApiToken(db.Model):
    """Tokens de API para integraciones externas"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Nombre descriptivo del token
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime)  # None = nunca expira
    
    created_by = db.relationship('User', backref=db.backref('api_tokens', lazy='dynamic'))
    
    def is_valid(self):
        """Verifica si el token está activo y no ha expirado"""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


class Integration(db.Model):
    """Configuración de integraciones con plataformas externas"""
    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(20), nullable=False)  # slack, teams, etc
    name = db.Column(db.String(100), nullable=False)  # Nombre descriptivo
    webhook_url = db.Column(db.String(500))  # URL del webhook para respuestas
    config = db.Column(db.Text)  # Configuración adicional (JSON)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime)
    
    created_by = db.relationship('User', backref=db.backref('integrations', lazy='dynamic'))


class AuditLog(db.Model):
    """Registro de auditoría para cambios sensibles y accesos"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)  # 'login', 'password_change', 'ticket_create', etc
    resource_type = db.Column(db.String(50))  # 'user', 'ticket', 'integration', etc
    resource_id = db.Column(db.Integer)  # ID del recurso afectado
    ip_address = db.Column(db.String(45))  # IPv4 o IPv6
    user_agent = db.Column(db.Text)  # Browser info
    status = db.Column(db.String(20), default='success')  # success, failure
    details = db.Column(db.Text)  # JSON serialized details
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))
    
    @staticmethod
    def log_action(user_id, action, resource_type=None, resource_id=None, ip_address=None, user_agent=None, status='success', details=None):
        """Helper method to log an action"""
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                details=details
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            # Don't let logging fail the application
            print(f'Failed to record audit log: {e}')


class PasswordHistory(db.Model):
    """Historial de contraseñas para prevenir reutilización"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    user = db.relationship('User', backref=db.backref('password_history', lazy='dynamic', cascade='all, delete-orphan'))
    
    @staticmethod
    def check_password_reuse(user_id, password, max_history=5):
        """Check if password has been used in last 5 password changes"""
        from werkzeug.security import check_password_hash
        
        history = PasswordHistory.query.filter_by(user_id=user_id).order_by(
            PasswordHistory.changed_at.desc()
        ).limit(max_history).all()
        
        for entry in history:
            if check_password_hash(entry.password_hash, password):
                return True
        return False
    
    @staticmethod
    def add_to_history(user_id, password_hash):
        """Add password to history"""
        history = PasswordHistory(user_id=user_id, password_hash=password_hash)
        db.session.add(history)
        db.session.commit()

