import os

from flask import Blueprint, render_template, session, redirect, request, url_for, jsonify
from flask_login import login_required, current_user

from app import translate
from app.ai_chatbot import answer_question, converse_with_assistant

bp = Blueprint('main', __name__)


def _assistant_title_from_message(message, lang):
    normalized = ' '.join((message or '').split())
    if not normalized:
        return translate('Support request', lang)
    return normalized[:137] + '...' if len(normalized) > 140 else normalized


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/pricing')
def pricing():
    lang = session.get('lang', 'es')
    return render_template(
        'pricing.html',
        monthly_price_display=os.environ.get(
            'PAYPAL_MONTHLY_PRICE_DISPLAY',
            '$29/mo' if lang == 'en' else 'US$29/mes',
        ).strip(),
        annual_price_display=os.environ.get(
            'PAYPAL_ANNUAL_PRICE_DISPLAY',
            '$290/yr' if lang == 'en' else 'US$290/año',
        ).strip(),
        annual_offer_text=os.environ.get(
            'PAYPAL_ANNUAL_OFFER_TEXT',
            'Get 2 months free (annual)' if lang == 'en' else 'Obtén 2 meses gratis pagando anual',
        ).strip(),
        has_monthly_price=bool(os.environ.get('PAYPAL_MONTHLY_PLAN_ID', '').strip()),
        has_annual_price=bool(os.environ.get('PAYPAL_ANNUAL_PLAN_ID', '').strip()),
    )


@bp.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy', 'service': 'soporte-tecnico'}), 200


@bp.route('/presence-ping', methods=['GET'])
@login_required
def presence_ping():
    """Lightweight endpoint to keep authenticated user presence up to date."""
    return ('', 204)


@bp.route('/assistant/chat', methods=['POST'])
@login_required
def assistant_chat():
    """User-facing support assistant endpoint for the floating chatbot."""
    lang = session.get('lang', 'es')
    data = request.get_json(silent=True) or {}
    message = ' '.join((data.get('message') or '').split())

    if len(message) < 3:
        return jsonify({
            'ok': False,
            'reply': translate('Please describe your issue in a bit more detail so I can help you better.', lang),
        }), 400

    # Get intelligent response from assistant (LLM with KB fallback)
    user_id = current_user.id
    result = converse_with_assistant(user_id, message, lang=lang)
    
    create_ticket_url = url_for(
        'tickets.create_ticket',
        title=_assistant_title_from_message(message, lang),
        description=message,
        category=result.get('ticket_category', ''),
    )

    # Return response with context for ticket creation
    response = {
        'ok': True,
        'reply': result['reply'],
        'confidence': result['confidence'],
        'used_llm': result.get('used_llm', False),
        'create_ticket_url': create_ticket_url,
        'create_ticket_label': translate('Create ticket with this context', lang),
    }
    
    # Add category if knowledge base was used or found
    if result.get('ticket_category'):
        response['category'] = result['ticket_category']
        response['category_label'] = translate(result['ticket_category'], lang)
    
    return jsonify(response)


@bp.route('/lang/<lang>')
def set_language(lang):
    if lang not in ('en', 'es'):
        lang = 'es'
    session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))


@bp.route('/quienes-somos')
def about_us():
    return render_template('about.html')


@bp.route('/contactanos')
def contact():
    return render_template('contact.html')


@bp.route('/servicios')
def services():
    return render_template('services.html')


@bp.route('/terminos-y-condiciones')
def terms_and_conditions():
    return render_template('terms.html')


