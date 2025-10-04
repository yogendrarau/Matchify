import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so 'Matchify' package can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')
import django
django.setup()
from django.db import connection

cur = connection.cursor()
print('TABLES:', connection.introspection.table_names())
cur.execute("SELECT app, name FROM django_migrations WHERE app='Matchifyapp'")
print('MIGRATIONS:', cur.fetchall())
