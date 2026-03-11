from app import create_app, send_email, send_webhook


app = create_app('config.TestingConfig')


def test_send_webhook_posts_when_configured(monkeypatch):
    captured = []

    class FakeResponse:
        status_code = 200

    def fake_post(url, json=None, **kwargs):
        captured.append((url, json))
        return FakeResponse()

    import requests

    monkeypatch.setattr(requests, 'post', fake_post)

    with app.app_context():
        app.config['CHAT_WEBHOOK_URL'] = 'https://hooks.example.com/test'
        send_webhook('hello webhook')

    assert len(captured) == 1
    assert captured[0][0] == 'https://hooks.example.com/test'
    assert captured[0][1]['text'] == 'hello webhook'


def test_send_email_triggers_webhook_when_mail_suppressed(monkeypatch):
    captured = []

    class FakeResponse:
        status_code = 200

    def fake_post(url, json=None, **kwargs):
        captured.append((url, json))
        return FakeResponse()

    import requests

    monkeypatch.setattr(requests, 'post', fake_post)

    with app.app_context():
        app.config['MAIL_SUPPRESS_SEND'] = True
        app.config['CHAT_WEBHOOK_URL'] = 'https://hooks.example.com/test'
        send_email('subject', ['admin@example.com'], 'ticket body')

    assert len(captured) == 1
    assert captured[0][1]['text'] == 'ticket body'
