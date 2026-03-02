import requests

session = requests.Session()
base = 'http://127.0.0.1:5000'
# fetch login page to get CSRF
r = session.get(base + '/auth/login')
from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, 'html.parser')
csrf = soup.find('input', {'id': 'csrf_token'})['value']
print('csrf', csrf)
# post credentials
r2 = session.post(base + '/auth/login', data={'username': 'admin', 'password': 'admin', 'csrf_token': csrf})
print('status', r2.status_code, 'url', r2.url)
print(r2.text[:1000])
