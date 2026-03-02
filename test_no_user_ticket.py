from app import create_app, db
from app.models import User, Ticket

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password})


def test_detail_ticket_without_user():
    with app.app_context():
        # ensure schema is up-to-date for this test run
        db.drop_all()
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@example.com', role='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
        t = Ticket(title='anon', description='no user', category='Red', priority='Baja', creator_name='Anon Person')
        db.session.add(t)
        db.session.commit()
        tid = t.id
    with app.test_client() as client:
        login(client, 'admin', 'admin')
        r = client.get(f'/tickets/{tid}')
        assert r.status_code == 200
        assert b'Created by:' in r.data  # should render label even if value blank
        assert b'Creator:' in r.data  # our new field should always show a label
        # ensure no server error message
        assert b'Internal Server Error' not in r.data


if __name__ == '__main__':
    test_detail_ticket_without_user()