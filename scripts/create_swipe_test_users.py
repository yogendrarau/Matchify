#!/usr/bin/env python3
"""
Create several test users with bios so you can swipe on them in Discover.
Run from repo root:
    python3 scripts/create_swipe_test_users.py
"""
import os
import django
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')
import sys
sys.path.insert(0, PROJECT_ROOT)

django.setup()

from django.contrib.auth import get_user_model
from Matchifyapp.models import Profile

User = get_user_model()

users = [
    ('alice', 'Alice — indie/alt head. I like late-night guitar vibes.'),
    ('ben', 'Ben — rap & trap. Concert-goer and coffee addict.'),
    ('cara', 'Cara — pop and R&B lover, vinyl collector.'),
    ('dan', 'Dan — emo and punk. Skater, photographer.'),
    ('eve', 'Eve — electronic, synths and chillwave.'),
    ('finn', 'Finn — singer-songwriter, guitar, and lo-fi playlists.')
]

password = 'TestUser123!'

created = []
for username, bio in users:
    user, created_flag = User.objects.get_or_create(username=username, defaults={'email': f'{username}@example.com'})
    user.set_password(password)
    user.save()
    p, _ = Profile.objects.get_or_create(user=user)
    p.bio = bio
    p.save()
    created.append((username, password, bio))

print('Created/updated test users:')
for u,pw,bio in created:
    print(f'- {u} / {pw} — bio: "{bio}"')

print('\nYou can login as any of these users from the Discover page and swipe on other users.\n')
