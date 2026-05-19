from app import create_app, db
from app.models import User
from bs4 import BeautifulSoup

app = create_app()
# keep CSRF enabled
app.config['WTF_CSRF_ENABLED'] = True

with app.app_context():
    u = User.query.filter_by(username='admin').first()
    if not u:
        u = User(username='admin', email='admin@example.com', role='admin')
        u.set_password('admin')
        db.session.add(u)
        db.session.commit()

    with app.test_client() as client:
        r = client.get('/?open_login=1')
        soup = BeautifulSoup(r.data, 'html.parser')
        token = soup.find('input', {'name': 'csrf_token'})['value']
        print('obtained csrf', token)
        r2 = client.post('/auth/login', data={'username':'admin','password':'admin','csrf_token':token}, follow_redirects=True)
        print('post status', r2.status_code)
        print(r2.data.decode('utf-8')[:1000])
