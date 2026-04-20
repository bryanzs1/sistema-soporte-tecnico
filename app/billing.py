import json
import os
from datetime import datetime, timezone

import stripe
from flask import Blueprint, current_app, jsonify, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import BillingEvent, Company

bp = Blueprint('billing', __name__)

stripe.api_key = os.environ.get('STRIPE_API_KEY', '').strip()

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _stripe_is_configured():
    api_key = os.environ.get('STRIPE_API_KEY', '').strip()
    if not api_key:
        return False
    stripe.api_key = api_key
    return True

def _admin_company_required():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Debes iniciar sesión.'}), 401, None
    if not current_user.is_admin():
        return jsonify({'error': 'Se requieren permisos de administrador.'}), 403, None
    if not current_user.company_id:
        return jsonify({'error': 'Tu usuario no tiene empresa asignada.'}), 400, None
    company = Company.query.get(current_user.company_id)
    if not company:
        return jsonify({'error': 'Empresa no encontrada.'}), 404, None
    return None, None, company

def _get_or_create_customer(company):
    if company.stripe_customer_id:
        return company.stripe_customer_id

    customer = stripe.Customer.create(
        name=company.name,
        metadata={'company_id': str(company.id)},
    )
    company.stripe_customer_id = customer.id
    db.session.commit()
    return customer.id


def _get_current_company():
    if not current_user.is_authenticated or not current_user.company_id:
        return None
    return db.session.get(Company, current_user.company_id)

def _record_billing_event(company_id, event):
    event_id = event.get('id')
    if not event_id:
        return None

    existing = BillingEvent.query.filter_by(event_id=event_id).first()
    if existing:
        return existing

    created_unix = event.get('created')
    created_at = utcnow()
    if created_unix:
        created_at = datetime.fromtimestamp(created_unix, tz=timezone.utc).replace(tzinfo=None)

    billing_event = BillingEvent(
        company_id=company_id,
        event_type=event.get('type', 'unknown'),
        event_id=event_id,
        created_at=created_at,
        data=json.dumps(event),
    )
    db.session.add(billing_event)
    return billing_event

def _update_company_from_subscription(company, subscription):
    if not subscription:
        return
    company.stripe_subscription_id = subscription.get('id')
    company.stripe_price_id = (
        subscription.get('items', {})
        .get('data', [{}])[0]
        .get('price', {})
        .get('id')
    )
    period_end = subscription.get('current_period_end')
    if period_end:
        company.stripe_current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc).replace(tzinfo=None)
    company.stripe_cancel_at_period_end = bool(subscription.get('cancel_at_period_end'))

def create_customer_and_subscription(name, email, price_id, payment_method, customer_id=None, company=None):
    try:
        if not _stripe_is_configured():
            return {
                'success': False,
                'error': 'Stripe no está configurado en el servidor.',
            }

        stripe_payment_method = stripe.PaymentMethod.retrieve(payment_method)
        attached_customer_id = getattr(stripe_payment_method, 'customer', None)
        payment_method_id = stripe_payment_method.id

        company_customer_id = company.stripe_customer_id if company else None

        if company_customer_id and attached_customer_id and company_customer_id != attached_customer_id:
            return {
                'success': False,
                'error': 'El método de pago pertenece a un customer distinto al registrado para esta empresa.',
            }

        resolved_customer_id = company_customer_id or attached_customer_id or customer_id

        if resolved_customer_id:
            customer = stripe.Customer.modify(
                resolved_customer_id,
                name=name,
                email=email,
                description='Cliente de membresía',
            )
        else:
            customer = stripe.Customer.create(
                name=name,
                email=email,
                description='Cliente de membresía',
            )

        if company and company.stripe_customer_id != customer.id:
            company.stripe_customer_id = customer.id
            db.session.commit()

        if attached_customer_id and attached_customer_id != customer.id:
            return {
                'success': False,
                'error': 'El método de pago ya está asociado a otro cliente en Stripe.',
            }

        if not attached_customer_id:
            stripe_payment_method = stripe.PaymentMethod.attach(payment_method, customer=customer.id)
            payment_method_id = stripe_payment_method.id

        stripe.Customer.modify(
            customer.id,
            invoice_settings={'default_payment_method': payment_method_id},
        )

        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': price_id}],
            default_payment_method=payment_method_id,
        )

        return {
            'success': True,
            'customer_id': customer.id,
            'subscription_id': subscription.id,
        }
    except stripe.error.StripeError as e:
        return {
            'success': False,
            'error': str(e),
        }

@bp.route('/billing/create-membership', methods=['POST'])
def create_membership():
    data = request.get_json(silent=True) or {}
    company = _get_current_company()

    name = data.get('name')
    email = data.get('email')
    price_id = data.get('price_id')
    payment_method = data.get('payment_method')
    customer_id = data.get('customer_id')

    print(f"[Stripe] payment_method recibido: {payment_method}")
    print(f"[Stripe] customer_id recibido: {customer_id}")

    if not name or not email or not price_id or not payment_method:
        return jsonify({'success': False, 'error': 'Faltan datos'}), 400

    result = create_customer_and_subscription(
        name,
        email,
        price_id,
        payment_method,
        customer_id=customer_id,
        company=company,
    )
    if result['success']:
        return jsonify({
            'success': True,
            'customer_id': result['customer_id'],
            'subscription_id': result['subscription_id'],
        }), 201

    return jsonify({'success': False, 'error': result['error']}), 400

@bp.route('/billing/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    error_response, status_code, company = _admin_company_required()
    if error_response:
        return error_response, status_code

    if not _stripe_is_configured():
        return jsonify({'error': 'Stripe no está configurado en el servidor.'}), 500

    price_id = (company.stripe_price_id or os.environ.get('STRIPE_DEFAULT_PRICE_ID', '')).strip()
    if not price_id:
        return jsonify({'error': 'No hay un precio Stripe configurado para esta empresa.'}), 400

    try:
        customer_id = _get_or_create_customer(company)
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            metadata={'company_id': str(company.id)},
            success_url=url_for('admin.settings_billing', _external=True) + '?billing=success',
            cancel_url=url_for('admin.settings_billing', _external=True) + '?billing=canceled',
        )
        return jsonify({'checkout_url': checkout_session.url})
    except Exception as exc:
        current_app.logger.error('Stripe checkout session error: %s', exc)
        return jsonify({'error': 'No se pudo iniciar la sesión de pago.'}), 500


@bp.route('/billing/create-portal-session', methods=['POST'])
@login_required
def create_portal_session():
    error_response, status_code, company = _admin_company_required()
    if error_response:
        return error_response, status_code

    if not _stripe_is_configured():
        return jsonify({'error': 'Stripe no está configurado en el servidor.'}), 500

    if not company.stripe_customer_id:
        return jsonify({'error': 'La empresa aún no tiene cliente Stripe.'}), 400

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=company.stripe_customer_id,
            return_url=url_for('admin.settings_billing', _external=True),
        )
        return jsonify({'portal_url': portal_session.url})
    except Exception as exc:
        current_app.logger.error('Stripe portal session error: %s', exc)
        return jsonify({'error': 'No se pudo abrir el portal de facturación.'}), 500


@bp.route('/billing/webhook/stripe', methods=['POST'])
def stripe_webhook():
    if not _stripe_is_configured():
        return 'Stripe not configured', 503

    payload = request.data
    signature = request.headers.get('Stripe-Signature', '')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '').strip()

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        else:
            event = json.loads(payload.decode('utf-8'))
    except Exception as exc:
        current_app.logger.warning('Invalid Stripe webhook: %s', exc)
        return 'Invalid webhook', 400

    event_type = event.get('type')
    event_object = event.get('data', {}).get('object', {})
    metadata = event_object.get('metadata', {}) if isinstance(event_object, dict) else {}

    company = None
    company_id = metadata.get('company_id')
    customer_id = event_object.get('customer') if isinstance(event_object, dict) else None

    if company_id:
        company = Company.query.get(int(company_id))
    if not company and customer_id:
        company = Company.query.filter_by(stripe_customer_id=customer_id).first()

    if not company:
        current_app.logger.warning('Stripe webhook without matching company: %s', event_type)
        return '', 200

    _record_billing_event(company.id, event)

    if customer_id and not company.stripe_customer_id:
        company.stripe_customer_id = customer_id

    if event_type == 'checkout.session.completed':
        subscription_id = event_object.get('subscription')
        company.billing_status = 'active'
        company.is_active = True
        if subscription_id:
            company.stripe_subscription_id = subscription_id
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
                _update_company_from_subscription(company, subscription)
            except Exception as exc:
                current_app.logger.warning('Unable to retrieve Stripe subscription %s: %s', subscription_id, exc)

    elif event_type == 'customer.subscription.updated':
        _update_company_from_subscription(company, event_object)
        company.billing_status = event_object.get('status') or company.billing_status or 'active'

    elif event_type == 'customer.subscription.deleted':
        _update_company_from_subscription(company, event_object)
        company.billing_status = 'canceled'
        company.is_active = False

    elif event_type == 'invoice.payment_succeeded':
        company.billing_status = 'active'
        company.is_active = True
        company.stripe_last_payment = utcnow()
        company.stripe_last_invoice_url = event_object.get('hosted_invoice_url') or company.stripe_last_invoice_url
        subscription_id = event_object.get('subscription')
        if subscription_id and not company.stripe_subscription_id:
            company.stripe_subscription_id = subscription_id

    elif event_type == 'invoice.payment_failed':
        company.billing_status = 'past_due'
        company.stripe_last_invoice_url = event_object.get('hosted_invoice_url') or company.stripe_last_invoice_url

    db.session.commit()
    return '', 200
