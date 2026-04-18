from app import create_app, db
from app.models import ApiToken, Company, Integration, Ticket, User
import json

app = create_app('config.TestingConfig')
app.config['WTF_CSRF_ENABLED'] = False

def login(client, username, password):
    return client.post(
        '/auth/login',
        data={'username': username, 'password': password},
        follow_redirects=True,
    )

def seed_office365_data():
    with app.app_context():
        db.drop_all()
        db.create_all()

        company_a = Company(name='Empresa A', description='Tenant A')
        company_b = Company(name='Empresa B', description='Tenant B')
        db.session.add_all([company_a, company_b])
        db.session.flush()

        admin_a = User(
            username='admin_a',
            email='admin_a@eie-puj.com',
            role='admin',
            company_id=company_a.id,
        )
        admin_a.set_password('secret123A!')

        admin_b = User(
            username='admin_b',
            email='admin_b@eie-puj.com',
            role='admin',
            company_id=company_b.id,
        )
        admin_b.set_password('secret123B!')

        db.session.add_all([admin_a, admin_b])
        db.session.flush()

        token_a = ApiToken(
            name='Token Empresa A',
            token='token-company-a',
            company_id=company_a.id,
            created_by_id=admin_a.id,
            is_active=True,
        )
        token_b = ApiToken(
            name='Token Empresa B',
            token='token-company-b',
            company_id=company_b.id,
            created_by_id=admin_b.id,
            is_active=True,
        )
        integration_a = Integration(
            platform='office365_email',
            name='Office365 Empresa A',
            company_id=company_a.id,
            created_by_id=admin_a.id,
            is_active=True,
            config=json.dumps({'enabled': True, 'mailbox': 'soporte@empresa-a.com', 'allow_external_senders': False}),
        )
        integration_b = Integration(
            platform='office365_email',
            name='Office365 Empresa B',
            company_id=company_b.id,
            created_by_id=admin_b.id,
            is_active=True,
            config=json.dumps({'enabled': True, 'mailbox': 'soporte@empresa-b.com', 'allow_external_senders': True}),
        )
        db.session.add_all([token_a, token_b, integration_a, integration_b])
        db.session.commit()
        return {
            'company_a_id': company_a.id,
            'company_b_id': company_b.id,
            'token_a': token_a.token,
            'token_b': token_b.token,
            'integration_a_id': integration_a.id,
            'integration_b_id': integration_b.id,
        }

def test_office365_email_intake_isolated_by_company():
    ids = seed_office365_data()
    payload = {
        'subject': 'Prueba O365 Empresa A',
        'body': 'Cuerpo del correo de prueba',
        'from_email': 'empleado@empresa-a.com',
        'from_name': 'Empleado A',
        'message_id': 'msgid-empresa-a',
        'category': 'Soporte',
        'priority': 'Alta',
    }
    with app.test_client() as client:
        # Empresa A: intake debe funcionar
        resp_a = client.post(
            '/api/v1/email/intake',
            json=payload,
            headers={'X-API-Token': ids['token_a']},
        )
        assert resp_a.status_code == 201
        data_a = resp_a.get_json()
        assert data_a['success'] is True
        # Empresa B: intake debe funcionar (allow_external_senders True)
        resp_b = client.post(
            '/api/v1/email/intake',
            json={**payload, 'from_email': 'externo@otrodominio.com'},
            headers={'X-API-Token': ids['token_b']},
        )
        assert resp_b.status_code == 201
        # Empresa A: intake rechaza remitente externo (allow_external_senders False)
        resp_a_ext = client.post(
            '/api/v1/email/intake',
            json={**payload, 'from_email': 'externo@otrodominio.com'},
            headers={'X-API-Token': ids['token_a']},
        )
        assert resp_a_ext.status_code == 403
        # Empresa B: intake rechaza si integration deshabilitada
        with app.app_context():
            integration_b = Integration.query.get(ids['integration_b_id'])
            integration_b.config = json.dumps({'enabled': False, 'mailbox': 'soporte@empresa-b.com', 'allow_external_senders': True})
            db.session.commit()
        resp_b_disabled = client.post(
            '/api/v1/email/intake',
            json=payload,
            headers={'X-API-Token': ids['token_b']},
        )
        assert resp_b_disabled.status_code == 503
