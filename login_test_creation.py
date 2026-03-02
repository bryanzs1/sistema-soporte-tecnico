from app import create_app, db
from app.models import User, Ticket

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['LOGIN_DISABLED'] = False
app.config['TESTING'] = True
# avoid actual SMTP connections during tests
app.config['MAIL_SUPPRESS_SEND'] = True


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password})


def test_ticket_creation():
    with app.test_client() as client:
        # ensure admin user exists
        with app.app_context():
            if not User.query.filter_by(username='admin').first():
                u = User(username='admin', email='admin@example.com', role='admin')
                u.set_password('admin')
                db.session.add(u)
                db.session.commit()
        # login
        resp = login(client, 'admin', 'admin')
        assert resp.status_code == 302
        # get create page
        r = client.get('/tickets/create')
        assert b'Create a new ticket' in r.data
        # post new ticket
        r2 = client.post('/tickets/create', data={
            'title': 'Test', 'description': 'Desc', 'category': 'Red', 'priority': 'Baja'
        }, follow_redirects=True)
        assert b'Ticket created successfully' in r2.data
        assert b'Test' in r2.data


if __name__ == '__main__':
    test_ticket_creation()
