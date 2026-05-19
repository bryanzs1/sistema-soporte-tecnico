from app import create_app, db
from app.models import User, Ticket

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password})


def prepare():
    with app.app_context():
        db.drop_all()
        db.create_all()
        # create admin and tech
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('admin')
        tech = User(username='tech', email='tech@empresa.com', role='technician')
        tech.set_password('tech')
        user = User(username='joe', email='joe@empresa.com')
        user.set_password('joe')
        db.session.add_all([admin, tech, user])
        # add some tickets
        t1 = Ticket(title='T1', description='d', category='Red', priority='Baja', creator_name='A', user=admin)
        t2 = Ticket(title='T2', description='d', category='Hardware', priority='Alta', creator_name='B', user=tech, status='Cerrado')
        db.session.add_all([t1, t2])
        db.session.commit()


def test_dashboard_access():
    prepare()
    with app.test_client() as c:
        # anonymous should redirect
        r = c.get('/admin/dashboard')
        assert r.status_code in (302,)
        # regular user forbidden
        login(c, 'joe', 'joe')
        r2 = c.get('/admin/dashboard')
        assert r2.status_code in (302, 403)
        c.get('/auth/logout')
        # technician can access
        login(c, 'tech', 'tech')
        r3 = c.get('/admin/dashboard')
        assert r3.status_code == 200
        assert b'Total tickets' in r3.data
        assert b'href="/tickets/?status=Abierto"' in r3.data
        assert b'T1' not in r3.data  # stats view doesn't show individual titles
        c.get('/auth/logout')
        # admin can access
        login(c, 'admin', 'admin')
        r4 = c.get('/admin/dashboard')
        assert r4.status_code == 200
        assert b'Operations Hub' in r4.data
        # should also have a link for "In Progress" card (space may be encoded)
        assert b'status=En' in r4.data and b'proceso' in r4.data


if __name__ == '__main__':
    test_dashboard_access()