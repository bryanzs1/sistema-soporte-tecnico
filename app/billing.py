import json
import os
from datetime import datetime, timezone

import requests
from flask import Blueprint, current_app, jsonify, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import BillingEvent, Company

bp = Blueprint('billing', __name__)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_paypal_datetime(value):
    if not value:
        return None
    normalized = value.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(normalized).astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return None


def _paypal_api_base_url():
    custom_base = os.environ.get('PAYPAL_API_BASE', '').strip()
    if custom_base:
        return custom_base.rstrip('/')

    mode = os.environ.get('PAYPAL_MODE', 'sandbox').strip().lower()
    if mode == 'live':
        return 'https://api-m.paypal.com'
    return 'https://api-m.sandbox.paypal.com'


def _paypal_web_base_url():
    mode = os.environ.get('PAYPAL_MODE', 'sandbox').strip().lower()
    if mode == 'live':
        return 'https://www.paypal.com'
    return 'https://www.sandbox.paypal.com'


def _paypal_is_configured():
    client_id = os.environ.get('PAYPAL_CLIENT_ID', '').strip()
    client_secret = os.environ.get('PAYPAL_CLIENT_SECRET', '').strip()
    return bool(client_id and client_secret)


def _paypal_client_id():
    return os.environ.get('PAYPAL_CLIENT_ID', '').strip()


def _paypal_client_secret():
    return os.environ.get('PAYPAL_CLIENT_SECRET', '').strip()


def _admin_company_required():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Debes iniciar sesión.'}), 401, None
    if not current_user.is_admin():
        return jsonify({'error': 'Se requieren permisos de administrador.'}), 403, None
    if not current_user.company_id:
        return jsonify({'error': 'Tu usuario no tiene empresa asignada.'}), 400, None
    company = db.session.get(Company, current_user.company_id)
    if not company:
        return jsonify({'error': 'Empresa no encontrada.'}), 404, None
    return None, None, company


def _get_current_company():
    if not current_user.is_authenticated or not current_user.company_id:
        return None
    return db.session.get(Company, current_user.company_id)


def _resolve_paypal_plan_id(company, requested_plan=None):
    requested_plan = (requested_plan or '').strip().lower()

    if requested_plan == 'monthly':
        return os.environ.get('PAYPAL_MONTHLY_PLAN_ID', '').strip()
    if requested_plan == 'annual':
        return os.environ.get('PAYPAL_ANNUAL_PLAN_ID', '').strip()

    return (company.stripe_price_id or os.environ.get('PAYPAL_DEFAULT_PLAN_ID', '')).strip()


def _paypal_manage_subscription_url(subscription_id):
    if not subscription_id:
        return None
    return f"{_paypal_web_base_url()}/myaccount/autopay/connect/{subscription_id}"


def _get_paypal_access_token():
    if not _paypal_is_configured():
        raise RuntimeError('PayPal no está configurado en el servidor.')

    response = requests.post(
        f"{_paypal_api_base_url()}/v1/oauth2/token",
        auth=(_paypal_client_id(), _paypal_client_secret()),
        data={'grant_type': 'client_credentials'},
        headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get('access_token', '').strip()
    if not access_token:
        raise RuntimeError('PayPal no devolvió un access token válido.')
    return access_token


def _paypal_request(method, path, *, token=None, json_body=None, expected_statuses=None):
    expected_statuses = expected_statuses or {200}
    request_headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    if token:
        request_headers['Authorization'] = f'Bearer {token}'

    response = requests.request(
        method,
        f"{_paypal_api_base_url()}{path}",
        headers=request_headers,
        json=json_body,
        timeout=30,
    )

    payload = {}
    if response.text:
        try:
            payload = response.json()
        except ValueError:
            payload = {'raw': response.text}

    if response.status_code not in expected_statuses:
        message = payload.get('message') or payload.get('error_description') or payload.get('raw') or 'PayPal request failed.'
        raise RuntimeError(message)

    return payload, response


def _extract_paypal_link(payload, rel):
    for link in payload.get('links', []) or []:
        if link.get('rel') == rel:
            return link.get('href')
    return None


def _record_billing_event(company_id, event):
    event_id = event.get('id') or event.get('resource', {}).get('id')
    if not event_id:
        return None

    existing = BillingEvent.query.filter_by(event_id=event_id).first()
    if existing:
        return existing

    created_at = _parse_paypal_datetime(event.get('create_time')) or utcnow()
    billing_event = BillingEvent(
        company_id=company_id,
        event_type=event.get('event_type', 'unknown'),
        event_id=event_id,
        created_at=created_at,
        data=json.dumps(event),
    )
    db.session.add(billing_event)
    return billing_event


def _update_company_from_paypal_subscription(company, subscription):
    if not subscription:
        return

    company.stripe_subscription_id = subscription.get('id') or company.stripe_subscription_id
    company.stripe_price_id = subscription.get('plan_id') or company.stripe_price_id

    subscriber = subscription.get('subscriber', {}) if isinstance(subscription, dict) else {}
    payer_reference = subscriber.get('payer_id') or subscriber.get('email_address')
    if payer_reference:
        company.stripe_customer_id = payer_reference

    billing_info = subscription.get('billing_info', {}) if isinstance(subscription, dict) else {}
    next_billing_time = billing_info.get('next_billing_time')
    if next_billing_time:
        company.stripe_current_period_end = _parse_paypal_datetime(next_billing_time)

    last_payment = billing_info.get('last_payment', {}) if isinstance(billing_info, dict) else {}
    last_payment_time = last_payment.get('time')
    if last_payment_time:
        company.stripe_last_payment = _parse_paypal_datetime(last_payment_time)

    paypal_status = (subscription.get('status') or '').upper()
    status_map = {
        'ACTIVE': 'active',
        'APPROVAL_PENDING': 'inactive',
        'APPROVED': 'inactive',
        'SUSPENDED': 'past_due',
        'CANCELLED': 'canceled',
        'EXPIRED': 'canceled',
    }
    mapped_status = status_map.get(paypal_status)
    if mapped_status:
        company.billing_status = mapped_status
        company.is_active = mapped_status == 'active'

    company.stripe_cancel_at_period_end = paypal_status in {'CANCELLED', 'EXPIRED'}
    company.stripe_last_invoice_url = _paypal_manage_subscription_url(company.stripe_subscription_id)


def _verify_paypal_webhook(event):
    webhook_id = os.environ.get('PAYPAL_WEBHOOK_ID', '').strip()
    if not webhook_id:
        return True

    token = _get_paypal_access_token()
    payload = {
        'auth_algo': request.headers.get('PAYPAL-AUTH-ALGO', ''),
        'cert_url': request.headers.get('PAYPAL-CERT-URL', ''),
        'transmission_id': request.headers.get('PAYPAL-TRANSMISSION-ID', ''),
        'transmission_sig': request.headers.get('PAYPAL-TRANSMISSION-SIG', ''),
        'transmission_time': request.headers.get('PAYPAL-TRANSMISSION-TIME', ''),
        'webhook_id': webhook_id,
        'webhook_event': event,
    }

    verification, _response = _paypal_request(
        'POST',
        '/v1/notifications/verify-webhook-signature',
        token=token,
        json_body=payload,
        expected_statuses={200},
    )
    return verification.get('verification_status') == 'SUCCESS'


def _find_company_from_paypal_event(resource):
    if not isinstance(resource, dict):
        return None, None

    company_id = resource.get('custom_id')
    subscription_id = resource.get('id') or resource.get('billing_agreement_id')

    company = None
    if company_id:
        try:
            company = db.session.get(Company, int(company_id))
        except (TypeError, ValueError):
            company = None

    if not company and subscription_id:
        company = Company.query.filter_by(stripe_subscription_id=subscription_id).first()

    return company, subscription_id


def _fetch_paypal_subscription(subscription_id):
    token = _get_paypal_access_token()
    subscription, _response = _paypal_request(
        'GET',
        f'/v1/billing/subscriptions/{subscription_id}',
        token=token,
        expected_statuses={200},
    )
    return subscription


@bp.route('/billing/create-membership', methods=['POST'])
def create_membership():
    return jsonify({
        'success': False,
        'error': 'Este flujo directo con método de pago ya no está disponible. Usa PayPal Checkout desde la página de precios.',
    }), 410


@bp.route('/billing/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    error_response, status_code, company = _admin_company_required()
    if error_response:
        return error_response, status_code

    if not _paypal_is_configured():
        return jsonify({'error': 'PayPal no está configurado en el servidor.'}), 500

    data = request.get_json(silent=True) or {}
    requested_plan = data.get('plan')
    plan_id = _resolve_paypal_plan_id(company, requested_plan=requested_plan)
    if not plan_id:
        return jsonify({'error': 'No hay un plan de PayPal configurado para esta selección.'}), 400

    try:
        token = _get_paypal_access_token()
        payload = {
            'plan_id': plan_id,
            'custom_id': str(company.id),
            'application_context': {
                'brand_name': 'Soporte IT Pro',
                'user_action': 'SUBSCRIBE_NOW',
                'return_url': url_for('admin.settings_billing', _external=True) + '?billing=success',
                'cancel_url': url_for('admin.settings_billing', _external=True) + '?billing=canceled',
            },
        }

        response_payload, _response = _paypal_request(
            'POST',
            '/v1/billing/subscriptions',
            token=token,
            json_body=payload,
            expected_statuses={200, 201},
        )

        approval_url = _extract_paypal_link(response_payload, 'approve')
        if not approval_url:
            return jsonify({'error': 'PayPal no devolvió un enlace de aprobación para la suscripción.'}), 502

        company.stripe_subscription_id = response_payload.get('id') or company.stripe_subscription_id
        company.stripe_price_id = plan_id
        company.stripe_last_invoice_url = _paypal_manage_subscription_url(company.stripe_subscription_id)
        db.session.commit()

        return jsonify({'checkout_url': approval_url})
    except Exception as exc:
        current_app.logger.error('PayPal subscription creation error: %s', exc)
        return jsonify({'error': 'No se pudo iniciar la suscripción en PayPal.'}), 500


@bp.route('/billing/create-portal-session', methods=['POST'])
@login_required
def create_portal_session():
    error_response, status_code, company = _admin_company_required()
    if error_response:
        return error_response, status_code

    if not _paypal_is_configured():
        return jsonify({'error': 'PayPal no está configurado en el servidor.'}), 500

    if not company.stripe_subscription_id:
        return jsonify({'error': 'La empresa aún no tiene una suscripción de PayPal activa o pendiente.'}), 400

    return jsonify({'portal_url': _paypal_manage_subscription_url(company.stripe_subscription_id)})


@bp.route('/billing/webhook/paypal', methods=['POST'])
def paypal_webhook():
    if not _paypal_is_configured():
        return 'PayPal not configured', 503

    event = request.get_json(silent=True) or {}
    try:
        if not _verify_paypal_webhook(event):
            current_app.logger.warning('Invalid PayPal webhook signature.')
            return 'Invalid webhook', 400
    except Exception as exc:
        current_app.logger.warning('PayPal webhook verification error: %s', exc)
        return 'Invalid webhook', 400

    event_type = event.get('event_type', '')
    resource = event.get('resource', {}) if isinstance(event.get('resource', {}), dict) else {}
    company, subscription_id = _find_company_from_paypal_event(resource)

    if not company:
        current_app.logger.warning('PayPal webhook without matching company: %s', event_type)
        return '', 200

    _record_billing_event(company.id, event)

    try:
        if event_type in {
            'BILLING.SUBSCRIPTION.CREATED',
            'BILLING.SUBSCRIPTION.ACTIVATED',
            'BILLING.SUBSCRIPTION.UPDATED',
            'BILLING.SUBSCRIPTION.RE-ACTIVATED',
            'BILLING.SUBSCRIPTION.SUSPENDED',
            'BILLING.SUBSCRIPTION.CANCELLED',
            'BILLING.SUBSCRIPTION.EXPIRED',
        }:
            if subscription_id:
                try:
                    subscription = _fetch_paypal_subscription(subscription_id)
                except Exception as exc:
                    current_app.logger.warning('Unable to retrieve PayPal subscription %s: %s', subscription_id, exc)
                    subscription = resource
            else:
                subscription = resource
            _update_company_from_paypal_subscription(company, subscription)

        elif event_type == 'PAYMENT.SALE.COMPLETED':
            company.billing_status = 'active'
            company.is_active = True
            if subscription_id and not company.stripe_subscription_id:
                company.stripe_subscription_id = subscription_id
            company.stripe_last_invoice_url = _paypal_manage_subscription_url(company.stripe_subscription_id or subscription_id)
            payment_time = resource.get('create_time') or event.get('create_time')
            parsed_payment_time = _parse_paypal_datetime(payment_time)
            if parsed_payment_time:
                company.stripe_last_payment = parsed_payment_time

        elif event_type in {'BILLING.SUBSCRIPTION.PAYMENT.FAILED', 'PAYMENT.SALE.REVERSED', 'PAYMENT.SALE.REFUNDED'}:
            company.billing_status = 'past_due'
            company.is_active = False
            if subscription_id and not company.stripe_subscription_id:
                company.stripe_subscription_id = subscription_id
            company.stripe_last_invoice_url = _paypal_manage_subscription_url(company.stripe_subscription_id or subscription_id)

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('PayPal webhook processing error: %s', exc)
        return 'Webhook processing error', 500

    return '', 200


@bp.route('/billing/webhook/stripe', methods=['POST'])
def legacy_stripe_webhook():
    return 'Stripe webhook disabled', 410
