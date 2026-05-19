from app import create_app, db
from app.models import User, Ticket

app = create_app()
# disable CSRF for testing convenience and use console mail backend
app.config['WTF_CSRF_ENABLED'] = False
app.config['MAIL_SUPPRESS_SEND'] = True  # avoid sending during tests
with app.app_context():
    # rebuild schema to ensure it includes the new column
    db.drop_all()
    db.create_all()
    u = User.query.filter_by(username='admin').first()
    if not u:
        u = User(username='admin', email='admin@example.com', role='admin')
        u.set_password('admin')
        db.session.add(u)
        db.session.commit()

    if Ticket.query.count() == 0:
        t = Ticket(title='Test', description='Desc', category='Red', priority='Baja', creator_name='Test Creator', user=u)
        db.session.add(t)
        db.session.commit()

    with app.test_client() as c:
        # login
        r = c.post('/auth/login', data={'username':'admin','password':'admin'}, follow_redirects=True)
        print('post login status', r.status_code, 'path', r.request.path)
        r = c.get('/tickets/?status=Abierto')
        print('list status page', r.status_code)
        r = c.get('/tickets/export?status=Abierto')
        print('export status page', r.status_code)
        print(r.data.decode('utf-8')[:200])
