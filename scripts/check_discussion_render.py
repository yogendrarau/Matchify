import os
import sys
# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
User = get_user_model()
username = 'smoketestuser'
password = 'password123'
# Create user if not exists
if not User.objects.filter(username=username).exists():
    User.objects.create_user(username=username, email='smoke@example.com', password=password)

c = Client()
logged_in = c.login(username=username, password=password)
print('logged_in', logged_in)
resp = c.get('/discussion/')
print('status_code', resp.status_code)
content = resp.content.decode('utf-8')
found = 'form[action^="/react/"]' in content or 'Intercept reaction forms' in content or 'Intercep' in content
print('ajax_selector_present', found)
# show snippet around our script if present
if found:
    idx = content.find('form[action')
    start = max(0, idx-200)
    end = min(len(content), idx+400)
    print(content[start:end])
else:
    # search for our moved script block
    if 'Intercept reaction forms' in content:
        print('found helper comment')
    else:
        # print small tail of HTML to help debug
        print(content[-800:])
