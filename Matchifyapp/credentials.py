import os

# Prefer environment variables so deployed environments can configure Spotify credentials.
# These defaults are only for local development and should be overridden in production.
CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '0976f4dc50654bde9738bc83b6187113')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', 'f5944f2ffe0d4c358d58fabf185bb28f')
# The env var may be set to the base URL; ensure the app uses the full redirect path.
_raw_redirect = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://http://3.17.60.99:8000/')
# Ensure redirect ends with the expected path the app exposes.
if _raw_redirect.endswith('/'):
	REDIRECT_URI = _raw_redirect + 'redirect/' if not _raw_redirect.endswith('/redirect/') else _raw_redirect
else:
	REDIRECT_URI = _raw_redirect + '/redirect'
