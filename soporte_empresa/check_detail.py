from app import create_app, db
from app.models import User, Ticket

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
with app.app_context():
    # refresh schema and ensure user
    db.drop_all()
    db.create_all()
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
    # create ticket
    t = Ticket(title='foo', description='bar', category='Red', priority='Baja', creator_name='Foo Bar', user=admin)
    db.session.add(t)
    db.session.commit()
    tid = t.id

with app.test_client() as c:
    # login
    c.post('/auth/login', data={'username':'admin','password':'admin'})
    r = c.get(f'/tickets/{tid}')
    print('detail status', r.status_code)
    print(r.data[:500])
