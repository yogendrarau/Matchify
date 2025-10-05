import os
import sys
import django
# Ensure project root is on sys.path so Django can import the project package
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')
django.setup()
from Matchifyapp.models import Profile
from django.conf import settings

print('MEDIA_ROOT:', settings.MEDIA_ROOT)
print('Profiles:')
for p in Profile.objects.select_related('user'):
    img = getattr(p, 'image', None)
    name = getattr(img, 'name', None) if img else None
    url = None
    try:
        url = img.url if img and getattr(img, 'url', None) else None
    except Exception as e:
        url = f'error getting url: {e}'
    exists = False
    if name:
        path = os.path.join(settings.MEDIA_ROOT, name)
        exists = os.path.exists(path)
    print(f'- {p.user.username}: image.name={name!r}, url={url!r}, file_exists={exists}')
