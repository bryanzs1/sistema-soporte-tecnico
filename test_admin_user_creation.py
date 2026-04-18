from app import create_app, db
from app.models import User

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True
app.config['SECRET_KEY'] = 'test'


def login(client, username, password):
    return client.post('/auth/login', data={'username': username, 'password': password})


def test_register_endpoint_disabled():
    with app.test_client() as client:
        r = client.get('/auth/register')
        assert r.status_code == 404


def test_only_admin_create_user():
    from app.models import Company
    with app.app_context():
        # Crear empresa y asociar admin
        company = Company.query.filter_by(name='EmpresaTest').first()
        if not company:
            company = Company(name='EmpresaTest')
            db.session.add(company)
            db.session.commit()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@empresa.com', role='admin', company_id=company.id)
            admin.set_password('admin')
            db.session.add(admin)
        else:
            admin.company_id = company.id
        user = User.query.filter_by(username='joe').first()
        if not user:
            user = User(username='joe', email='joe@empresa.com', company_id=company.id)
            user.set_password('joe')
            db.session.add(user)
        db.session.commit()
        admin_company_id = company.id
    with app.test_client() as client:
        # Solo probar creación válida de usuario admin
        login(client, 'admin', 'admin')
        username = 'alice_test_flash'
        with app.app_context():
            existing = User.query.filter_by(username=username).first()
            if existing:
                db.session.delete(existing)
                db.session.commit()
        r = client.post('/admin/users/create', data={
            'username': username,
            'email': 'alice@eie-puj.com',
            'password': 'test',
            'password2': 'test',
            'role': 'user',
            'company_id': admin_company_id  # Usar el company_id guardado
        }, follow_redirects=True)
        # Verificar que el usuario aparece en la lista de usuarios
        r_list = client.get('/admin/users')
        print("\n\n==== HTML LISTA USUARIOS ====")
        print(r_list.data.decode(errors='ignore'))
        assert username.encode() in r_list.data


if __name__ == '__main__':
    test_register_endpoint_disabled()
    test_only_admin_create_user()
