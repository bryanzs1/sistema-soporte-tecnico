from app import create_app, db
from app.models import User, Ticket

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
        r = c.get('/tickets/export?format=csv')
        print('csv type', r.mimetype, 'len', len(r.data))
        r2 = c.get('/tickets/export?format=xlsx')
        print('xlsx type', r2.mimetype, 'len', len(r2.data))
