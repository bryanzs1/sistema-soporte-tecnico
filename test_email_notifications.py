from app import create_app, db, mail
from app.models import User, Ticket

app = create_app()
# disable CSRF so forms pass in tests
app.config['WTF_CSRF_ENABLED'] = False
app.config['MAIL_SUPPRESS_SEND'] = True  # do not attempt real SMTP connection
app.config['MAIL_SERVER'] = 'localhost'
app.config['MAIL_PORT'] = 25
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@test'

with app.app_context():
    # rebuild schema before running notifications tests
    db.drop_all()
    db.create_all()
    # ensure admin exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('admin')
        db.session.add(admin)
    else:
        admin.role = 'admin'
    db.session.commit()

    # configure webhook URL so send_webhook will fire
    app.config['CHAT_WEBHOOK_URL'] = 'https://hooks.example.com/test'

    messages = []
    slack_posts = []

    def fake_send(subject, recipients, body, html=None):
        messages.append((subject, recipients, body))
        # also trigger webhook path so we can assert on slack_posts
        _app_module.send_webhook(body)

    # patch send_email helper
    import app as _app_module
    _app_module.send_email = fake_send

    # patch requests.post for webhook capture
    import requests
    orig_post = requests.post
    def fake_post(url, json=None, **kwargs):
        slack_posts.append((url, json))
        class R:
            status_code = 200
        return R
    requests.post = fake_post

    with app.test_client() as c:
        r = c.post('/auth/login', data={'username':'admin','password':'admin'})
        print('login status', r.status_code)
        # create ticket via form to invoke notification
        r = c.post('/tickets/create', data={
            'title':'NotifTest',
            'creator_name':'Tester',
            'description':'desc',
            'category':'Red',
            'priority':'Baja'
        }, follow_redirects=True)
        print('create status', r.status_code)
        print(r.data.decode('utf-8')[:200])
        print('messages after creation', messages)
        # ensure both email and webhook were invoked
        assert len(messages) == 1
        assert 'NotifTest' in messages[0][2]
        assert len(slack_posts) == 1
        assert slack_posts[0][0] == app.config['CHAT_WEBHOOK_URL']
        assert 'NotifTest' in slack_posts[0][1]['text']

        # update ticket status through detail view
        t = Ticket.query.filter_by(title='NotifTest').first()
        messages.clear()
        slack_posts.clear()
        r2 = c.post(f'/tickets/{t.id}', data={'status':'Cerrado'}, follow_redirects=True)
        print('update status', r2.status_code)
        print(r2.data.decode('utf-8')[:200])
        print('messages after update', messages)
        assert len(messages) == 1
        assert ('Cerrado' in messages[0][2]) or ('Closed' in messages[0][2])
        assert len(slack_posts) == 1
        assert ('Cerrado' in slack_posts[0][1]['text']) or ('Closed' in slack_posts[0][1]['text'])
        # restore original requests
    requests.post = orig_post
