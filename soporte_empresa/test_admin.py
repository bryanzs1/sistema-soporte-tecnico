from app import create_app, db
from app.models import User

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False

with app.app_context():
    u = User.query.filter_by(username='admin').first()
    if not u:
        u = User(username='admin', email='admin@example.com', role='admin')
        u.set_password('admin')
        db.session.add(u)
        db.session.commit()

    with app.test_client() as c:
        c.post('/auth/login', data={'username':'admin','password':'admin'})
        r = c.get('/admin/users')
        print('users page', r.status_code)
        print(r.data.decode('utf-8')[:500])
        # edit self role to technician
        r2 = c.post(f'/admin/users/{u.id}/edit', data={'role':'technician'})
        print('edit status', r2.status_code)
        print('new role', u.role)
