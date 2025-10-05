"""Simple smoke tests using Django test client.

This script will:
- Create a temporary test user
- POST to /edit-bio to set the bio
- GET the profile page and check the bio appears in the response content
- POST to /discussion/ to create a post
- GET /discussion/ and check the post content appears

Run with the project's Django settings (from repo root):
python scripts/smoke_test_endpoints.py
"""

import os
import django

# Setup Django environment
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')
import sys
sys.path.insert(0, PROJECT_ROOT)

django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from Matchifyapp.models import Profile, Post


def run():
    User = get_user_model()
    username = 'smoketestuser'
    password = 'Sm0keTestPass!'

    # Ensure test user exists (create or reuse); set password to known value
    user, created = User.objects.get_or_create(username=username, defaults={'email': 'smoke@example.com'})
    user.set_password(password)
    user.save()
    print(('Created test user:' if created else 'Reused test user:'), user.username)

    client = Client()
    logged_in = client.login(username=username, password=password)
    print('Logged in:', logged_in)

    # Test edit-bio
    bio_text = 'Smoke test bio ' + username
    resp = client.post('/edit-bio', {'bio': bio_text}, follow=True)
    print('/edit-bio POST status:', resp.status_code)

    # Fetch profile page
    profile_resp = client.get(f'/profile/{username}/')
    print('/profile/ GET status:', profile_resp.status_code)
    if bio_text in profile_resp.content.decode('utf-8'):
        print('Bio found in profile page HTML')
    else:
        print('Bio NOT found in profile page HTML')

    # Test discussion post
    post_text = 'Smoke test post content ' + username
    resp2 = client.post('/discussion/', {'content': post_text}, follow=True)
    print('/discussion/ POST status:', resp2.status_code)

    disc_resp = client.get('/discussion/')
    print('/discussion/ GET status:', disc_resp.status_code)
    if post_text in disc_resp.content.decode('utf-8'):
        print('Post found in discussion page HTML')
    else:
        print('Post NOT found in discussion page HTML')

    # Inspect DB objects
    try:
        p = Profile.objects.filter(user=user).first()
        print('Profile in DB:', bool(p), 'bio=', getattr(p, 'bio', None))
    except Exception as e:
        print('Error fetching Profile from DB:', e)

    try:
        posts = Post.objects.filter(author=user)
        print('Posts in DB (count):', posts.count())
        if posts.exists():
            print('Latest post content:', posts.latest('created_at').content)
    except Exception as e:
        print('Error fetching Post from DB:', e)


if __name__ == '__main__':
    run()
