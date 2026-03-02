from app import create_app

app = create_app()
app.config['TESTING'] = True
with app.test_client() as client:
    r = client.get('/')
    print('status', r.status_code)
    print('contains bootswatch:', b'bootswatch' in r.data)
    print('contains style.css:', b'style.css' in r.data)