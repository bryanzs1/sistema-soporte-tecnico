from datetime import datetime
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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_technician(self):
        return self.role == 'technician'


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
