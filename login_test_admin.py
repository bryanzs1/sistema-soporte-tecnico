from app import create_app, db
from app.models import User

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False  # simplify testing
with app.app_context():
    u = User.query.filter_by(username='admin').first()
    print('admin exists?', u)
    if not u:
        u = User(username='admin', email='admin@example.com', role='admin')
        u.set_password('admin')
        db.session.add(u)
        db.session.commit()
        print('created admin')
    else:
        print('admin password correct?', u.check_password('admin'))

with app.test_client() as c:
    r = c.post('/auth/login', data={'username':'admin', 'password':'admin'}, follow_redirects=True)
    print('status', r.status_code)
    print('final path', r.request.path)
    print(r.data.decode('utf-8')[:1000])
