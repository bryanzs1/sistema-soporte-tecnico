from app import create_app, db
from app.models import ApiToken, Company, Integration, Ticket, User


app = create_app('config.TestingConfig')
app.config['WTF_CSRF_ENABLED'] = False


def login(client, username, password):
    return client.post(
        '/auth/login',
        data={'username': username, 'password': password},
        follow_redirects=True,
    )


def seed_data():
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

        tech_a = User(
            username='tech_a',
            email='tech_a@eie-puj.com',
            role='technician',
            company_id=company_a.id,
        )
        tech_a.set_password('secret123T!')

        db.session.add_all([admin_a, admin_b, tech_a])
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
            platform='slack',
            name='Slack Empresa A',
            company_id=company_a.id,
            created_by_id=admin_a.id,
            is_active=True,
        )
        integration_b = Integration(
            platform='teams',
            name='Teams Empresa B',
            company_id=company_b.id,
            created_by_id=admin_b.id,
            is_active=True,
        )

        db.session.add_all([token_a, token_b, integration_a, integration_b])
        db.session.commit()

        return {
            'company_a_id': company_a.id,
            'company_b_id': company_b.id,
            'token_a_id': token_a.id,
            'token_b_id': token_b.id,
            'integration_a_id': integration_a.id,
            'integration_b_id': integration_b.id,
        }


def test_settings_integrations_scope_by_company():
    ids = seed_data()

    with app.test_client() as client:
        login(client, 'admin_a', 'secret123A!')
        response = client.get('/admin/settings/integrations')
        html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Token Empresa A' in html
    assert 'Slack Empresa A' in html
    assert 'Token Empresa B' not in html
    assert 'Teams Empresa B' not in html

    with app.test_client() as client:
        login(client, 'admin_a', 'secret123A!')
        revoke_response = client.post(f"/admin/integrations/tokens/{ids['token_b_id']}/revoke")
        delete_response = client.post(f"/admin/integrations/{ids['integration_b_id']}/delete")

    assert revoke_response.status_code == 404
    assert delete_response.status_code == 404


def test_api_token_creates_ticket_inside_token_company_only():
    ids = seed_data()

    with app.test_client() as client:
        create_response = client.post(
            '/api/v1/tickets',
            json={
                'title': 'VPN caída',
                'description': 'No conecta desde casa',
                'creator_name': 'Usuario API',
                'creator_email': 'tech_a@eie-puj.com',
                'category': 'VPN y conectividad remota',
                'priority': 'Alta',
            },
            headers={'X-API-Token': 'token-company-a'},
        )

        body = create_response.get_json()
        ticket_id = body['ticket']['id']
        get_response = client.get(
            f'/api/v1/tickets/{ticket_id}',
            headers={'Authorization': 'Bearer token-company-a'},
        )
        forbidden_response = client.get(
            f'/api/v1/tickets/{ticket_id}',
            headers={'Authorization': 'Bearer token-company-b'},
        )

    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert forbidden_response.status_code == 404

    with app.app_context():
        ticket = Ticket.query.get(ticket_id)
        token_a = ApiToken.query.get(ids['token_a_id'])
        token_b = ApiToken.query.get(ids['token_b_id'])

        assert ticket is not None
        assert ticket.company_id == ids['company_a_id']
        assert ticket.user.email == 'tech_a@eie-puj.com'
        assert token_a.last_used_at is not None
        assert token_b.last_used_at is not None