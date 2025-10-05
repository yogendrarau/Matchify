import os
import sys

# Ensure we run from project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Matchify.settings')

import django
django.setup()

from django.db import connection

TEST_DB_NAME = 'test_matchifydb'

print('Using DB settings:', connection.settings_dict.get('NAME'))

cur = connection.cursor()
try:
    cur.execute("SELECT pid, usename, application_name, client_addr FROM pg_stat_activity WHERE datname=%s AND pid <> pg_backend_pid();", [TEST_DB_NAME])
    rows = cur.fetchall()
    if not rows:
        print('No other sessions found for', TEST_DB_NAME)
    else:
        print('Found sessions:')
        for pid, usename, appname, client in rows:
            print(f'  pid={pid} user={usename} app={appname} client={client}')
        # Attempt to terminate
        results = []
        for pid, _, _, _ in rows:
            try:
                cur.execute('SELECT pg_terminate_backend(%s);', [pid])
                res = cur.fetchone()
                print(f'Terminate pid={pid} -> {res}')
                results.append((pid, res))
            except Exception as e:
                print('Failed to terminate pid=', pid, 'error=', e)
                results.append((pid, False, str(e)))
except Exception as e:
    print('Error querying pg_stat_activity:', e)

print('Done')
