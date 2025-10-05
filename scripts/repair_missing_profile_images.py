import os
import sys
import django
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')
django.setup()
from Matchifyapp.models import Profile
from django.conf import settings

changed = []
for p in Profile.objects.select_related('user'):
    img = getattr(p, 'image', None)
    name = getattr(img, 'name', None) if img else None
    if name:
        path = os.path.join(settings.MEDIA_ROOT, name)
        if not os.path.exists(path):
            print(f"Clearing missing image for {p.user.username} (was {name})")
            p.image = None
            p.save()
            changed.append(p.user.username)

print('Done. Cleared images for:', changed)
