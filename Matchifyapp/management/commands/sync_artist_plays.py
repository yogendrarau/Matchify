from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from ...models import ArtistListen
from ...views import get_auth_header, get_token
import requests
import time

class Command(BaseCommand):
    help = 'Sync last 50 recently-played tracks for each user and update ArtistListen play_count'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.filter(is_active=True)
        for user in users:
            try:
                token = get_token(user)
                if not token:
                    self.stdout.write(f"Skipping {user.username}: no token")
                    continue
                headers = get_auth_header(user)
                if not headers:
                    self.stdout.write(f"Skipping {user.username}: no auth headers")
                    continue
                url = 'https://api.spotify.com/v1/me/player/recently-played?limit=50'
                resp = requests.get(url, headers=headers)
                if resp.status_code != 200:
                    self.stdout.write(f"User {user.username}: Spotify API returned {resp.status_code}")
                    continue
                data = resp.json()
                items = data.get('items', [])
                # Count artist occurrences and accumulate ms for primary artist
                counts = {}
                ms = {}
                for it in items:
                    track = it.get('track')
                    if not track:
                        continue
                    duration = track.get('duration_ms', 0) or 0
                    artists = track.get('artists', [])
                    if not artists:
                        continue
                    # Use first artist as primary
                    artist = artists[0]
                    aid = artist.get('id')
                    name = artist.get('name')
                    counts[aid] = counts.get(aid, 0) + 1
                    ms[aid] = ms.get(aid, 0) + duration

                # Update DB rows
                for aid, cnt in counts.items():
                    # attempt to get a name from the first matching track's artist
                    # we didn't store a mapping earlier, so try to find any track with this artist id
                    name = None
                    for it in items:
                        track = it.get('track')
                        if not track:
                            continue
                        artists = track.get('artists', [])
                        if not artists:
                            continue
                        a0 = artists[0]
                        if a0.get('id') == aid:
                            name = a0.get('name')
                            break

                    try:
                        # Create or update: overwrite play_count with the last-50 count (sliding window)
                        listen, created = ArtistListen.objects.get_or_create(
                            user=user, artist_id=aid,
                            defaults={'artist_name': name or '', 'play_count': 0, 'total_ms': 0}
                        )
                        listen.play_count = cnt
                        listen.total_ms = ms.get(aid, 0)
                        # update artist_name if missing or different
                        if name and listen.artist_name != name:
                            listen.artist_name = name
                        listen.save()
                    except Exception as e:
                        self.stdout.write(f"Error updating ArtistListen for {user.username} {aid}: {e}")

                # Be courteous with Spotify rate limits
                time.sleep(0.15)
            except Exception as e:
                self.stdout.write(f"Unexpected error for {user.username}: {e}")
