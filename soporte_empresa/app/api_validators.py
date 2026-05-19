"""API validation schemas using Marshmallow"""

from marshmallow import Schema, fields, validate, ValidationError, pre_load, post_load
from datetime import datetime


class TicketCreateSchema(Schema):
    """Validate ticket creation payload"""
    title = fields.Str(required=True, validate=validate.Length(min=5, max=140))
    description = fields.Str(required=True, validate=validate.Length(min=10, max=5000))
    creator_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    category = fields.Str(required=True, validate=validate.Length(min=2, max=64))
    priority = fields.Str(required=True, validate=validate.OneOf(['Baja', 'Media', 'Alta', 'Crítica']))
    
    @pre_load
    def process_data(self, data, **kwargs):
        """Clean input data"""
        if isinstance(data, dict):
            # Strip whitespace from strings
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = value.strip()
        return data


class TicketUpdateSchema(Schema):
    """Validate ticket update payload"""
    status = fields.Str(required=True, validate=validate.OneOf(['Abierto', 'En proceso', 'Esperando usuario', 'Cerrado']))
    technician_id = fields.Int(allow_none=True)
    
    @post_load
    def validate_status(self, data, **kwargs):
        """Additional validation"""
        if data.get('status') not in ['Abierto', 'En proceso', 'Esperando usuario', 'Cerrado']:
            raise ValidationError('Invalid status value')
        return data


class TicketCommentSchema(Schema):
    """Validate ticket comment payload"""
    message = fields.Str(required=True, validate=validate.Length(min=1, max=5000))
    
    @pre_load
    def process_data(self, data, **kwargs):
        """Clean input"""
        if isinstance(data, dict) and 'message' in data:
            data['message'] = data['message'].strip()
        return data


class WebhookPayloadSchema(Schema):
    """Validate incoming webhook payloads from Slack/Teams"""
    event_type = fields.Str(required=True, validate=validate.OneOf(['ticket_created', 'ticket_updated', 'ticket_closed']))
    ticket_id = fields.Int(required=True)
    timestamp = fields.DateTime(required=True)
    data = fields.Dict(required=True)
    
    @post_load
    def validate_timestamp(self, data, **kwargs):
        """Ensure timestamp is not too old (prevent replay attacks)"""
        ts = data.get('timestamp')
        if isinstance(ts, datetime):
            # Allow 5 minute skew
            age_seconds = (datetime.utcnow() - ts).total_seconds()
            if age_seconds > 300:
                raise ValidationError('Timestamp too old (possible replay attack)')
        return data


class APITokenCreateSchema(Schema):
    """Validate API token creation"""
    name = fields.Str(required=True, validate=validate.Length(min=3, max=100))
    expires_in_days = fields.Int(allow_none=True, validate=validate.Range(min=1, max=365))


class IntegrationConfigSchema(Schema):
    """Validate integration configuration"""
    platform = fields.Str(required=True, validate=validate.OneOf(['slack', 'teams']))
    name = fields.Str(required=True, validate=validate.Length(min=3, max=100))
    webhook_url = fields.URL(required=True)
    config = fields.Dict(allow_none=True)


class PasswordResetSchema(Schema):
    """Validate password reset request"""
    email = fields.Email(required=True)


class PasswordChangeSchema(Schema):
    """Validate password change"""
    old_password = fields.Str(required=True, validate=validate.Length(min=1))
    new_password = fields.Str(required=True, validate=validate.Length(min=8))
    confirm_password = fields.Str(required=True)
    
    def validate_passwords_match(self, data):
        """Validate passwords match"""
        if data.get('new_password') != data.get('confirm_password'):
            raise ValidationError('Passwords do not match', field_name='confirm_password')
        if data.get('old_password') == data.get('new_password'):
            raise ValidationError('New password cannot be same as old', field_name='new_password')


# Helper function to validate API requests
def validate_request(schema_class, data=None):
    """
    Validate incoming request data
    
    Usage:
        from soporte_empresa.app.api_validators import validate_request, TicketCreateSchema
        
        errors = validate_request(TicketCreateSchema, request.json)
        if errors:
            return {'detail': errors}, 400
    """
    try:
        schema = schema_class()
        result = schema.load(data or {})
        return None  # No errors
    except ValidationError as e:
        return e.messages
