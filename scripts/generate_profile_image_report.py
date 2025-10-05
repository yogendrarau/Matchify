import os
import sys
import csv
import django
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')
django.setup()
from Matchifyapp.models import Profile
from django.conf import settings

out_path = os.path.join(os.path.dirname(__file__), 'profile_image_report.csv')
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['username', 'image_name', 'image_url', 'file_exists'])
    for p in Profile.objects.select_related('user'):
        img = getattr(p, 'image', None)
        name = getattr(img, 'name', None) if img else ''
        try:
            url = img.url if img and getattr(img, 'url', None) else ''
        except Exception:
            url = ''
        exists = False
        if name:
            path = os.path.join(settings.MEDIA_ROOT, name)
            exists = os.path.exists(path)
        writer.writerow([p.user.username, name or '', url or '', exists])

print('Wrote', out_path)
