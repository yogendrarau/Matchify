import os
import django
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')
import sys
sys.path.insert(0, str(PROJECT_ROOT))

django.setup()
from django.contrib.auth import get_user_model
from django.test import Client
from django.db import connection

User = get_user_model()
username = 'test_bio_user'
password = 'testpass123'
user, created = User.objects.get_or_create(username=username, defaults={'email':'test_bio@example.com'})
if created:
    user.set_password(password)
    user.save()
    print('Created user')
else:
    # ensure password is set
    user.set_password(password)
    user.save()
    print('User existed — password reset')

client = Client()
logged_in = client.login(username=username, password=password)
print('Logged in:', logged_in)

# Perform POST to edit-bio
resp = client.post('/edit-bio', {'bio': 'Hello from test script'})
print('POST status code:', resp.status_code)

# Query profile
from Matchifyapp.models import Profile
profile = Profile.objects.filter(user=user).first()
print('Profile exists:', bool(profile))
print('Profile bio:', getattr(profile, 'bio', None))

# Show session tmp

print('Done')
