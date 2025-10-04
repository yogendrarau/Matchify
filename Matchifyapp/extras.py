from .models import spotifyToken
from django.utils import timezone
from datetime import timedelta
from requests import post, get
from .credentials import CLIENT_ID, CLIENT_SECRET
BASE_URL = "http://api.spotify.com/v1/me/"

def check_spotifyTokens(user):
    tokens = spotifyToken.objects.filter(user=user)
    if tokens:
        return tokens[0]
    else:
        return None
    
def create_or_update_spotifyTokens(user, access_token, refresh_token, expires_in, token_type):
    tokens, created = spotifyToken.objects.get_or_create(
        user=user,
        defaults={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in,  # Pass the datetime object
            'token_type': token_type
        }
    )

    if not created:
        tokens.access_token = access_token
        tokens.refresh_token = refresh_token
        tokens.expires_in = expires_in
        tokens.token_type = token_type
        tokens.save(update_fields=['access_token', 'refresh_token', 'expires_in', 'token_type'])
    
def is_spotify_authenticated(user):
    tokens = spotifyToken.objects.filter(user=user).first()
    if tokens:
        expiry = tokens.expires_in
        if expiry <= timezone.now():
            success = refresh_spotify_token(user)
            return success
        return True
    return False

def refresh_spotify_token(user):
    tokens = spotifyToken.objects.filter(user=user).first()
    if not tokens:
        return False

    refresh_token = tokens.refresh_token
    response = post("https://accounts.spotify.com/api/token", data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }).json()

    access_token = response.get('access_token')
    token_type = response.get('token_type')
    expires_in = response.get('expires_in', 3600)  # Default to 1 hour if not provided
    
    # Only update if we got a valid response
    if access_token and token_type:
        # Calculate the expiration time
        expires_at = timezone.now() + timedelta(seconds=expires_in)

        create_or_update_spotifyTokens(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,  # Keep existing refresh token if not provided
            expires_in=expires_at,
            token_type=token_type
        )
        return True
    return False

def spotify_requests_execution(user, endpoint):
    tokens = check_spotifyTokens(user)
    if not tokens:
        return {'Error': 'No tokens found for this user.'}

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + tokens.access_token
    }
    response = get(BASE_URL + endpoint, {}, headers=headers)
    try:
        return response.json()
    except:
        return {'Error': 'Issue with request'}