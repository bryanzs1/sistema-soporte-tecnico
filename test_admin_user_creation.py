from app import create_app, db
from app.models import User

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password})


def test_register_endpoint_disabled():
    with app.test_client() as client:
        r = client.get('/auth/register')
        assert r.status_code == 404


def test_only_admin_create_user():
    with app.app_context():
        # ensure admin and normal user exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@empresa.com', role='admin')
            admin.set_password('admin')
            db.session.add(admin)
        user = User.query.filter_by(username='joe').first()
        if not user:
            user = User(username='joe', email='joe@empresa.com')
            user.set_password('joe')
            db.session.add(user)
        db.session.commit()
    with app.test_client() as client:
        # normal user should be redirected from create form
        login(client, 'joe', 'joe')
        r = client.get('/admin/users/create')
        assert r.status_code in (302, 403)  # redirect or forbidden
        client.get('/auth/logout')
        # admin can access
        login(client, 'admin', 'admin')
        r2 = client.get('/admin/users/create')
        assert r2.status_code == 200
        assert b'Create new user' in r2.data
        # submit form with invalid domains
        for bad in ['alice@gmail.com', 'alice@other.com']:
            r3 = client.post('/admin/users/create', data={
                'username': 'alice', 'email': bad,
                'password': 'test', 'password2': 'test', 'role': 'user'
            })
            assert b'Email must belong to one of' in r3.data
        # now valid domains, test each and clean up after
        allowed = ['@eie-puj.com', '@eie-lrm.com', '@bppclub.com']
        for dom in allowed:
            username = f'alice{dom.replace("@","_")}'
            existing = User.query.filter_by(username=username).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
            r4 = client.post('/admin/users/create', data={
                'username': username, 'email': f'alice{dom}',
                'password': 'test', 'password2': 'test', 'role': 'user'
            }, follow_redirects=True)
            assert b'User created' in r4.data
            assert User.query.filter_by(username=username).first() is not None


if __name__ == '__main__':
    test_register_endpoint_disabled()
    test_only_admin_create_user()
