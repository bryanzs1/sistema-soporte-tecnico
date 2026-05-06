@bp.route('/set-language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))


import os
from flask import Blueprint, render_template, session, redirect, request, url_for, jsonify, flash, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from app import db, translate
from app.ai_chatbot import answer_question, converse_with_assistant
from app.forms import TechnicianApplicationForm
from app.models import TechnicianApplication

bp = Blueprint('main', __name__)


def _t(text):
    return translate(text, session.get('lang', 'es'))


def _assistant_title_from_message(message, lang):
    normalized = ' '.join((message or '').split())
    if not normalized:
        return translate('Support request', lang)
    return normalized[:137] + '...' if len(normalized) > 140 else normalized


@bp.route('/')
def index():
    return render_template('index.html')


# Endpoint para solicitar acceso y demo
@bp.route('/solicitar-acceso', methods=['POST'])
def solicitar_acceso():
    nombre = request.form.get('nombre', '').strip()
    empresa = request.form.get('empresa', '').strip()
    correo = request.form.get('correo', '').strip()
    telefono = request.form.get('telefono', '').strip()
    mensaje = request.form.get('mensaje', '').strip()
    if not nombre or not correo:
        flash('Por favor completa los campos obligatorios.', 'danger')
        return redirect(url_for('main.index'))

    # Construir cuerpo del correo
    body = f"""
    Nueva solicitud de acceso/demo:
    Nombre: {nombre}
    Empresa: {empresa}
    Correo: {correo}
    Teléfono: {telefono}
    Mensaje: {mensaje}
    """
    subject = 'Nueva solicitud de acceso y demo'
    recipients = [current_app.config.get('MAIL_DEFAULT_SENDER')]
    # Permitir override por config
    demo_recipient = current_app.config.get('ACCESS_REQUEST_RECIPIENT')
    if demo_recipient:
        recipients = [demo_recipient]

    msg = Message(subject, recipients=recipients, body=body)
    try:
        current_app.extensions['mail'].send(msg)
        flash('¡Solicitud enviada correctamente! Nuestro equipo te contactará pronto.', 'success')
    except Exception as e:
        current_app.logger.error(f'Error enviando solicitud de acceso: {e}')
        flash('Ocurrió un error al enviar la solicitud. Intenta nuevamente.', 'danger')
    return redirect(url_for('main.index'))


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



@bp.route('/about-us')
def about_us():
    return render_template('about.html')

@bp.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy', 'service': 'soporte-tecnico'}), 200


@bp.route('/contactanos')
def contact():
    return render_template('contact.html')


@bp.route('/servicios')
def services():
    return render_template('services.html')


@bp.route('/solicitudes-tecnico', methods=['GET', 'POST'])
def technician_applications():
    form = TechnicianApplicationForm()

    if form.validate_on_submit():
        application = TechnicianApplication(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=(form.phone.data or '').strip(),
            location=(form.location.data or '').strip(),
            specialties=form.specialties.data.strip(),
            certifications=form.certifications.data.strip(),
            years_experience=int(form.years_experience.data or 0),
            professional_summary=(form.professional_summary.data or '').strip(),
            status='pending',
        )
        db.session.add(application)
        db.session.commit()
        flash(_t('Technician application submitted successfully. Our team will review your profile.'), 'success')
        return redirect(url_for('main.technician_applications'))

    return render_template('technician_application.html', form=form)


@bp.route('/terminos-y-condiciones')
def terms_and_conditions():
    return render_template('terms.html')


