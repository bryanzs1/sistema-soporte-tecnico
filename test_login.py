from app import create_app

app = create_app()

with app.test_client() as client:
    resp = client.get('/auth/login')
    print('GET /auth/login status', resp.status_code)
    print(resp.data.decode('utf-8'))

    resp2 = client.post('/auth/login', data={'username':'foo','password':'bar'})
    print('POST status', resp2.status_code)
    print(resp2.data.decode('utf-8'))
