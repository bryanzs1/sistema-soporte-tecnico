from app import create_app, login

app = create_app()
print('login callback in fresh app', login._user_callback)

with app.app_context():
    print('login callback inside app context', login._user_callback)
