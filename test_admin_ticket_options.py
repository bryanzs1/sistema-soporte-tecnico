from app import create_app, db
from app.models import User, TicketOption

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_admin_can_add_ticket_options():
    with app.app_context():
        db.drop_all()
        db.create_all()
        admin = User(username='admin', email='admin@empresa.com', role='admin')
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()

    with app.test_client() as client:
        login(client, 'admin', 'admin')

        r = client.post('/admin/ticket-options', data={
            'option_type': 'category',
            'value': 'Seguridad'
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Seguridad' in r.data

        r2 = client.post('/admin/ticket-options', data={
            'option_type': 'priority',
            'value': 'Urgente'
        }, follow_redirects=True)
        assert r2.status_code == 200
        assert b'Urgente' in r2.data

        r3 = client.get('/tickets/create')
        assert r3.status_code == 200
        assert b'Seguridad' in r3.data
        assert b'Urgente' in r3.data

        with app.app_context():
            category = TicketOption.query.filter_by(option_type='category', value='Seguridad').first()
            priority = TicketOption.query.filter_by(option_type='priority', value='Urgente').first()
            assert category is not None
            assert priority is not None

        r4 = client.post(f'/admin/ticket-options/{category.id}/edit', data={'value': 'Ciberseguridad'}, follow_redirects=True)
        assert r4.status_code == 200
        assert b'Ciberseguridad' in r4.data

        r5 = client.post(f'/admin/ticket-options/{priority.id}/edit', data={'value': 'Muy Alta'}, follow_redirects=True)
        assert r5.status_code == 200
        assert b'Muy Alta' in r5.data

        r6 = client.get('/tickets/create')
        assert r6.status_code == 200
        assert b'Ciberseguridad' in r6.data
        assert b'Muy Alta' in r6.data


if __name__ == '__main__':
    test_admin_can_add_ticket_options()
