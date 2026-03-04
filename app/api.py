"""
API Blueprint para integraciones externas (Slack, Teams, etc)
"""

import json
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import Ticket, User, ApiToken, Integration
from app.ai_sentiment import analyze_ticket as analyze_sentiment
from app.ai_chatbot import answer_question


bp = Blueprint('api', __name__)


def require_api_token(f):
    """Decorator para requerir autenticación con API token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_value = request.headers.get('X-API-Token') or request.headers.get('Authorization')
        
        if not token_value:
            return jsonify({'error': 'API token required'}), 401
        
        # Remover "Bearer " si existe
        if token_value.startswith('Bearer '):
            token_value = token_value[7:]
        
        token = ApiToken.query.filter_by(token=token_value).first()
        
        if not token or not token.is_valid():
            return jsonify({'error': 'Invalid or expired API token'}), 401
        
        # Actualizar last_used_at
        token.last_used_at = datetime.utcnow()
        db.session.commit()
        
        # Pasar el token al contexto
        request.api_token = token
        
        return f(*args, **kwargs)
    
    return decorated_function


@bp.route('/tickets', methods=['POST'])
@require_api_token
def create_ticket_api():
    """
    Crea un ticket via API
    
    Body JSON:
    {
        "title": "Título del ticket",
        "description": "Descripción detallada",
        "creator_name": "Nombre del creador",
        "creator_email": "email@ejemplo.com" (opcional),
        "category": "Software" (opcional),
        "priority": "Media" (opcional),
        "source": "slack" (opcional)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON body required'}), 400
        
        # Validaciones
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        creator_name = data.get('creator_name', '').strip()
        
        if not title:
            return jsonify({'error': 'title is required'}), 400
        
        if not description:
            return jsonify({'error': 'description is required'}), 400
        
        if not creator_name:
            return jsonify({'error': 'creator_name is required'}), 400
        
        # Datos opcionales
        creator_email = data.get('creator_email', '').strip()
        category = data.get('category') or Ticket.default_categories()[0]
        priority = data.get('priority') or 'Media'
        source = data.get('source', 'api')
        
        # Buscar o crear usuario basado en email
        user = None
        if creator_email:
            user = User.query.filter_by(email=creator_email).first()
        
        # Si no hay usuario, usar el que creó el token
        if not user:
            user = request.api_token.created_by
        
        # Crear ticket
        ticket = Ticket(
            title=title,
            description=description,
            creator_name=creator_name,
            category=category,
            priority=priority,
            user=user
        )
        
        # Calcular SLA
        ticket.sla_due_at = datetime.utcnow() + timedelta(hours=Ticket.sla_hours_by_priority(ticket.priority))
        
        # AI: Análisis de sentimiento
        try:
            sentiment_result = analyze_sentiment(title, description)
            ticket.sentiment_label = sentiment_result['sentiment_label']
            ticket.sentiment_score = sentiment_result['sentiment_score']
            ticket.urgency_level = sentiment_result['urgency_level']
        except Exception as e:
            current_app.logger.warning(f'Sentiment analysis failed: {e}')
        
        # AI: Buscar respuesta automática del chatbot
        try:
            chatbot_answer = answer_question(f"{title} {description}")
            if chatbot_answer and chatbot_answer['confidence'] >= 0.75:
                ticket.ai_response = chatbot_answer['answer']
                ticket.ai_response_id = chatbot_answer['kb_entry_id']
                ticket.ai_response_confidence = chatbot_answer['confidence']
        except Exception as e:
            current_app.logger.warning(f'Chatbot answer search failed: {e}')
        
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
            current_app.logger.warning(f'ML prediction failed: {e}')
        
        db.session.add(ticket)
        db.session.commit()
        
        # Preparar respuesta
        response = {
            'success': True,
            'ticket': {
                'id': ticket.id,
                'title': ticket.title,
                'description': ticket.description,
                'creator_name': ticket.creator_name,
                'category': ticket.category,
                'priority': ticket.priority,
                'status': ticket.status,
                'created_at': ticket.created_at.isoformat(),
                'sla_due_at': ticket.sla_due_at.isoformat() if ticket.sla_due_at else None,
                'auto_assigned': ticket.auto_assigned,
                'url': f"{request.url_root}tickets/{ticket.id}",
                # AI fields
                'sentiment': {
                    'label': ticket.sentiment_label,
                    'score': ticket.sentiment_score,
                    'urgency': ticket.urgency_level
                } if ticket.sentiment_label else None,
                'ai_response': ticket.ai_response,
                'ai_response_confidence': ticket.ai_response_confidence
            }
        }
        
        if ticket.technician:
            response['ticket']['assigned_to'] = ticket.technician.username
        
        return jsonify(response), 201
        
    except Exception as e:
        current_app.logger.error(f'Error creating ticket via API: {e}')
        db.session.rollback()
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500


@bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@require_api_token
def get_ticket_api(ticket_id):
    """Obtiene información de un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    
    return jsonify({
        'success': True,
        'ticket': {
            'id': ticket.id,
            'title': ticket.title,
            'description': ticket.description,
            'creator_name': ticket.creator_name,
            'category': ticket.category,
            'priority': ticket.priority,
            'status': ticket.status,
            'created_at': ticket.created_at.isoformat(),
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
            'sla_due_at': ticket.sla_due_at.isoformat() if ticket.sla_due_at else None,
            'assigned_to': ticket.technician.username if ticket.technician else None,
            'url': f"{request.url_root}tickets/{ticket.id}"
        }
    }), 200


@bp.route('/webhooks/slack', methods=['POST'])
def slack_webhook():
    """
    Webhook para recibir comandos desde Slack
    
    Ejemplo de comando slash en Slack:
    /ticket Impresora no funciona - No puedo imprimir documentos desde mi computadora
    """
    try:
        data = request.form
        
        # Validar token de Slack (si está configurado)
        integration = Integration.query.filter_by(platform='slack', is_active=True).first()
        if integration and integration.config:
            config = json.loads(integration.config)
            expected_token = config.get('verification_token')
            if expected_token and data.get('token') != expected_token:
                return jsonify({'error': 'Invalid verification token'}), 403
        
        # Parsear el texto del comando
        text = data.get('text', '').strip()
        user_name = data.get('user_name', 'Usuario Slack')
        
        if not text:
            return jsonify({
                'response_type': 'ephemeral',
                'text': '❌ Debes proporcionar descripción del problema.\nEjemplo: `/ticket Impresora no funciona - No puedo imprimir documentos`'
            })
        
        # Separar título y descripción (separados por " - ")
        if ' - ' in text:
            title, description = text.split(' - ', 1)
        else:
            # Si no hay separador, usar las primeras 50 caracteres como título
            title = text[:50]
            description = text
        
        # Buscar token API activo para crear el ticket
        api_token = ApiToken.query.filter_by(is_active=True).first()
        if not api_token:
            return jsonify({
                'response_type': 'ephemeral',
                'text': '❌ No hay tokens API configurados. Contacta al administrador.'
            })
        
        # Crear ticket
        user = api_token.created_by
        ticket = Ticket(
            title=title.strip(),
            description=description.strip(),
            creator_name=user_name,
            category='Software',  # Categoría por defecto para Slack
            priority='Media',
            user=user
        )
        
        ticket.sla_due_at = datetime.utcnow() + timedelta(hours=Ticket.sla_hours_by_priority(ticket.priority))
        
        # ML: Intentar auto-asignar
        try:
            from app.ml_classifier import classifier
            
            ticket_data = {
                'title': ticket.title,
                'description': ticket.description,
                'category': ticket.category,
                'priority': ticket.priority
            }
            
            predictions = classifier.predict(ticket_data, top_n=1)
            
            if predictions:
                suggested_tech_id, confidence = predictions[0]
                ticket.ml_suggested_technician_id = suggested_tech_id
                ticket.ml_confidence_score = confidence
                
                if confidence > 0.7:
                    ticket.technician_id = suggested_tech_id
                    ticket.auto_assigned = True
        except:pass
        
        db.session.add(ticket)
        db.session.commit()
        
        # Actualizar last_used en la integración
        if integration:
            integration.last_used_at = datetime.utcnow()
            db.session.commit()
        
        # Respuesta a Slack
        ticket_url = f"{request.url_root}tickets/{ticket.id}"
        assigned_to = f" y asignado a *{ticket.technician.username}*" if ticket.technician else ""
        
        return jsonify({
            'response_type': 'in_channel',
            'text': f'✅ Ticket creado exitosamente{assigned_to}',
            'attachments': [{
                'color': 'good',
                'fields': [
                    {'title': 'Ticket ID', 'value': f'#{ticket.id}', 'short': True},
                    {'title': 'Prioridad', 'value': ticket.priority, 'short': True},
                    {'title': 'Título', 'value': ticket.title, 'short': False},
                    {'title': 'Ver ticket', 'value': f'<{ticket_url}|Abrir en navegador>', 'short': False}
                ]
            }]
        })
        
    except Exception as e:
        current_app.logger.error(f'Slack webhook error: {e}')
        return jsonify({
            'response_type': 'ephemeral',
            'text': f'❌ Error al crear ticket: {str(e)}'
        })


@bp.route('/webhooks/teams', methods=['POST'])
def teams_webhook():
    """
    Webhook para recibir comandos desde Microsoft Teams
    
    Teams usa un formato similar pero con mensajes adaptivos
    """
    try:
        data = request.get_json()
        
        # Validar la integración
        integration = Integration.query.filter_by(platform='teams', is_active=True).first()
        
        # Extraer información del mensaje
        text = data.get('text', '').strip()
        from_name = data.get('from', {}).get('name', 'Usuario Teams')
        
        if not text:
            return jsonify({
                'type': 'message',
                'text': '❌ Debes proporcionar descripción del problema.\nEjemplo: `Impresora no funciona - No puedo imprimir documentos`'
            })
        
        # Parsear título y descripción
        if ' - ' in text:
            title, description = text.split(' - ', 1)
        else:
            title = text[:50]
            description = text
        
        # Buscar token API
        api_token = ApiToken.query.filter_by(is_active=True).first()
        if not api_token:
            return jsonify({
                'type': 'message',
                'text': '❌ No hay tokens API configurados. Contacta al administrador.'
            })
        
        # Crear ticket
        user = api_token.created_by
        ticket = Ticket(
            title=title.strip(),
            description=description.strip(),
            creator_name=from_name,
            category='Software',
            priority='Media',
            user=user
        )
        
        ticket.sla_due_at = datetime.utcnow() + timedelta(hours=Ticket.sla_hours_by_priority(ticket.priority))
        
        # ML: Intentar auto-asignar
        try:
            from app.ml_classifier import classifier
            
            ticket_data = {
                'title': ticket.title,
                'description': ticket.description,
                'category': ticket.category,
                'priority': ticket.priority
            }
            
            predictions = classifier.predict(ticket_data, top_n=1)
            
            if predictions:
                suggested_tech_id, confidence = predictions[0]
                ticket.ml_suggested_technician_id = suggested_tech_id
                ticket.ml_confidence_score = confidence
                
                if confidence > 0.7:
                    ticket.technician_id = suggested_tech_id
                    ticket.auto_assigned = True
        except:
            pass
        
        db.session.add(ticket)
        db.session.commit()
        
        # Actualizar integración
        if integration:
            integration.last_used_at = datetime.utcnow()
            db.session.commit()
        
        # Respuesta para Teams con Adaptive Card
        ticket_url = f"{request.url_root}tickets/{ticket.id}"
        assigned_to = f" y asignado a **{ticket.technician.username}**" if ticket.technician else ""
        
        return jsonify({
            'type': 'message',
            'attachments': [{
                'contentType': 'application/vnd.microsoft.card.adaptive',
                'content': {
                    'type': 'AdaptiveCard',
                    'version': '1.2',
                    'body': [
                        {
                            'type': 'TextBlock',
                            'text': f'✅ Ticket creado exitosamente{assigned_to}',
                            'weight': 'bolder',
                            'size': 'medium'
                        },
                        {
                            'type': 'FactSet',
                            'facts': [
                                {'title': 'Ticket ID:', 'value': f'#{ticket.id}'},
                                {'title': 'Prioridad:', 'value': ticket.priority},
                                {'title': 'Título:', 'value': ticket.title}
                            ]
                        }
                    ],
                    'actions': [
                        {
                            'type': 'Action.OpenUrl',
                            'title': 'Ver ticket',
                            'url': ticket_url
                        }
                    ]
                }
            }]
        })
        
    except Exception as e:
        current_app.logger.error(f'Teams webhook error: {e}')
        return jsonify({
            'type': 'message',
            'text': f'❌ Error al crear ticket: {str(e)}'
        })
