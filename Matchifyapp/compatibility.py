"""
Music Matching Algorithm for Matchify
Matches users based on their music taste (artists, tracks, genres)
"""

from collections import Counter
from django.contrib.auth import get_user_model
from .models import spotifyToken
import requests
from .credentials import CLIENT_ID, CLIENT_SECRET
import logging

logger = logging.getLogger(__name__)

class MusicMatchingAlgorithm:
    """
    Core algorithm for matching users based on music taste
    """
    
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
    
    def calculate_music_compatibility(self, user1, user2, time_range='long_term'):
        """
        Calculate music compatibility between two users (0-100 score)
        
        Args:
            user1: First user object
            user2: Second user object  
            time_range: 'short_term', 'medium_term', or 'long_term'
            
        Returns:
            dict: Compatibility score and breakdown
        """
        try:
            # Prefer the richer API-driven method
            user1_data = self._get_user_music_data(user1, time_range)
            user2_data = self._get_user_music_data(user2, time_range)

            if user1_data and user2_data:
                # Calculate individual compatibility scores
                artist_score = self._calculate_artist_compatibility(user1_data, user2_data)
                genre_score = self._calculate_genre_compatibility(user1_data, user2_data)
                track_score = self._calculate_track_compatibility(user1_data, user2_data)

                # Weighted final score
                weights = {'artist': 0.45, 'genre': 0.30, 'track': 0.25}
                total_score = (
                    artist_score * weights['artist'] +
                    genre_score * weights['genre'] +
                    track_score * weights['track']
                )

                return {
                    'total_score': round(total_score, 1),
                    'breakdown': {
                        'artist_compatibility': round(artist_score, 1),
                        'genre_compatibility': round(genre_score, 1),
                        'track_compatibility': round(track_score, 1)
                    },
                    'common_artists': self._get_common_artists(user1_data, user2_data),
                    'common_genres': self._get_common_genres(user1_data, user2_data),
                    'common_tracks': self._get_common_tracks(user1_data, user2_data)
                }

            # If we couldn't get full data from the API, fall back to a ranking/overlap based approach
            logger.debug('Falling back to ranking-overlap compatibility')
            from .views import get_top_artists

            u1_art = get_top_artists(user1, time_range) if get_top_artists else []
            u2_art = get_top_artists(user2, time_range) if get_top_artists else []

            # normalize lists to IDs and names
            def normalize_artists(artists):
                out = []
                if isinstance(artists, dict) and artists.get('Error'):
                    return out
                for i, a in enumerate(artists[:50]):
                    aid = a.get('id') if isinstance(a, dict) else None
                    name = a.get('name') if isinstance(a, dict) else str(a)
                    genres = a.get('genres', []) if isinstance(a, dict) else []
                    out.append({'id': aid, 'name': name, 'genres': genres, 'rank': i+1})
                return out

            na1 = normalize_artists(u1_art)
            na2 = normalize_artists(u2_art)

            # build rank maps
            rank1 = {a['id']: a['rank'] for a in na1 if a['id']}
            rank2 = {a['id']: a['rank'] for a in na2 if a['id']}

            # weight function (linear): higher rank => higher weight
            def rank_weight(rank):
                # rank in 1..50 -> weight between 1.0 and 0.02
                return max(0.02, (51 - rank) / 51)

            # artist score by weighted overlap
            common = set(rank1.keys()) & set(rank2.keys())
            artist_numer = 0.0
            artist_denom = 0.0
            for a in na1:
                if a['id']:
                    w = rank_weight(a['rank'])
                    artist_denom += w
                    if a['id'] in common:
                        artist_numer += w * rank_weight(rank2[a['id']])

            artist_score = (artist_numer / artist_denom * 100.0) if artist_denom > 0 else 0.0

            # track score: try to use tracks via _get_user_music_data, else 0
            u1_tracks = []
            u2_tracks = []
            try:
                d1 = self._get_user_music_data(user1, time_range) or {}
                d2 = self._get_user_music_data(user2, time_range) or {}
                u1_tracks = [t.get('id') for t in d1.get('tracks', [])[:50] if isinstance(t, dict) and t.get('id')]
                u2_tracks = [t.get('id') for t in d2.get('tracks', [])[:50] if isinstance(t, dict) and t.get('id')]
            except Exception:
                u1_tracks = []
                u2_tracks = []

            common_tracks = set(u1_tracks) & set(u2_tracks)
            track_score = 0.0
            if u1_tracks:
                # simple positional weighted score
                numer = 0.0
                denom = 0.0
                for i, tid in enumerate(u1_tracks[:50]):
                    w = rank_weight(i+1)
                    denom += w
                    if tid in common_tracks:
                        j = u2_tracks.index(tid)
                        numer += w * rank_weight(j+1)
                track_score = (numer / denom * 100.0) if denom > 0 else 0.0

            # genre score via Jaccard of top genres from artists
            g1 = set(g for a in na1 for g in a.get('genres', []))
            g2 = set(g for a in na2 for g in a.get('genres', []))
            inter = len(g1 & g2)
            union = len(g1 | g2)
            genre_score = (inter / union * 100.0) if union > 0 else 0.0

            # combine
            weights = {'artist': 0.45, 'genre': 0.30, 'track': 0.25}
            total = artist_score * weights['artist'] + genre_score * weights['genre'] + track_score * weights['track']

            return {
                'total_score': round(min(100.0, total), 1),
                'breakdown': {
                    'artist_compatibility': round(artist_score, 1),
                    'genre_compatibility': round(genre_score, 1),
                    'track_compatibility': round(track_score, 1)
                },
                'common_artists': list(common)[:10],
                'common_genres': list(g1 & g2)[:10],
                'common_tracks': list(common_tracks)[:10]
            }
        except Exception as e:
            logger.error(f"Error calculating music compatibility: {e}")
            return None
    
    def _get_user_music_data(self, user, time_range):
        """Get comprehensive music data for a user"""
        try:
            from .views import get_token, get_auth_header
            
            token = get_token(user)
            if not token:
                return None
            
            headers = get_auth_header(user)
            if not headers:
                return None
            
            # Get top artists
            artists_url = "https://api.spotify.com/v1/me/top/artists"
            artists_response = requests.get(artists_url, headers=headers, params={
                'time_range': time_range,
                'limit': 50
            })
            
            if artists_response.status_code != 200:
                return None
            
            artists_data = artists_response.json().get('items', [])
            
            # Get top tracks
            tracks_url = "https://api.spotify.com/v1/me/top/tracks"
            tracks_response = requests.get(tracks_url, headers=headers, params={
                'time_range': time_range,
                'limit': 50
            })
            
            if tracks_response.status_code != 200:
                return None
            
            tracks_data = tracks_response.json().get('items', [])
            
            return {
                'artists': artists_data,
                'tracks': tracks_data,
                'time_range': time_range
            }
            
        except Exception as e:
            logger.error(f"Error getting user music data: {e}")
            return None
    
    def _calculate_artist_compatibility(self, user1_data, user2_data):
        """Calculate artist-based compatibility (0-100)"""
        user1_artists = {artist['id']: artist for artist in user1_data['artists']}
        user2_artists = {artist['id']: artist for artist in user2_data['artists']}
        
        # Find common artists
        common_artists = set(user1_artists.keys()) & set(user2_artists.keys())
        
        if not common_artists:
            return 0
        
        # Calculate weighted score based on popularity ranks
        total_score = 0
        max_possible_score = 0
        
        for i, artist in enumerate(user1_data['artists']):
            weight = 1 / (i + 1)  # Higher weight for top artists
            max_possible_score += weight
            
            if artist['id'] in common_artists:
                # Find the rank in user2's list
                user2_rank = next((j for j, a in enumerate(user2_data['artists']) if a['id'] == artist['id']), 50)
                # Score decreases with rank difference
                rank_penalty = 1 / (abs(i - user2_rank) + 1)
                total_score += weight * rank_penalty
        
        return min(100, (total_score / max_possible_score) * 100) if max_possible_score > 0 else 0
    
    def _calculate_genre_compatibility(self, user1_data, user2_data):
        """Calculate genre-based compatibility (0-100)"""
        # Extract genres from artists
        user1_genres = []
        for artist in user1_data['artists']:
            user1_genres.extend(artist.get('genres', []))
        
        user2_genres = []
        for artist in user2_data['artists']:
            user2_genres.extend(artist.get('genres', []))
        
        if not user1_genres or not user2_genres:
            return 0
        
        # Calculate Jaccard similarity for genres
        user1_genre_set = set(user1_genres)
        user2_genre_set = set(user2_genres)
        
        intersection = len(user1_genre_set & user2_genre_set)
        union = len(user1_genre_set | user2_genre_set)
        
        jaccard_similarity = intersection / union if union > 0 else 0
        
        # Weight by genre frequency
        user1_genre_counts = Counter(user1_genres)
        user2_genre_counts = Counter(user2_genres)
        
        weighted_score = 0
        total_weight = 0
        
        for genre in user1_genre_set & user2_genre_set:
            weight = user1_genre_counts[genre] + user2_genre_counts[genre]
            weighted_score += weight
            total_weight += weight
        
        frequency_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Combine Jaccard similarity and frequency weighting
        final_score = (jaccard_similarity * 0.6 + frequency_score * 0.4) * 100
        
        return min(100, final_score)
    
    def _calculate_track_compatibility(self, user1_data, user2_data):
        """Calculate track-based compatibility (0-100)"""
        user1_tracks = {track['id']: track for track in user1_data['tracks']}
        user2_tracks = {track['id']: track for track in user2_data['tracks']}
        
        # Find common tracks
        common_tracks = set(user1_tracks.keys()) & set(user2_tracks.keys())
        
        if not common_tracks:
            return 0
        
        # Calculate weighted score based on track popularity ranks
        total_score = 0
        max_possible_score = 0
        
        for i, track in enumerate(user1_data['tracks']):
            weight = 1 / (i + 1)  # Higher weight for top tracks
            max_possible_score += weight
            
            if track['id'] in common_tracks:
                # Find the rank in user2's list
                user2_rank = next((j for j, t in enumerate(user2_data['tracks']) if t['id'] == track['id']), 50)
                # Score decreases with rank difference
                rank_penalty = 1 / (abs(i - user2_rank) + 1)
                total_score += weight * rank_penalty
        
        return min(100, (total_score / max_possible_score) * 100) if max_possible_score > 0 else 0
    
    def _get_common_artists(self, user1_data, user2_data):
        """Get list of common artists between users"""
        user1_artist_ids = {artist['id'] for artist in user1_data['artists']}
        user2_artist_ids = {artist['id'] for artist in user2_data['artists']}
        
        common_ids = user1_artist_ids & user2_artist_ids
        
        common_artists = []
        for artist in user1_data['artists']:
            if artist['id'] in common_ids:
                common_artists.append({
                    'name': artist['name'],
                    'id': artist['id'],
                    'genres': artist.get('genres', []),
                    'popularity': artist.get('popularity', 0)
                })
        
        return common_artists[:10]  # Return top 10 common artists
    
    def _get_common_genres(self, user1_data, user2_data):
        """Get list of common genres between users"""
        user1_genres = set()
        for artist in user1_data['artists']:
            user1_genres.update(artist.get('genres', []))
        
        user2_genres = set()
        for artist in user2_data['artists']:
            user2_genres.update(artist.get('genres', []))
        
        return list(user1_genres & user2_genres)[:10]
    
    def _get_common_tracks(self, user1_data, user2_data):
        """Get list of common tracks between users"""
        user1_track_ids = {track['id'] for track in user1_data['tracks']}
        user2_track_ids = {track['id'] for track in user2_data['tracks']}
        
        common_ids = user1_track_ids & user2_track_ids
        
        common_tracks = []
        for track in user1_data['tracks']:
            if track['id'] in common_ids:
                common_tracks.append({
                    'name': track['name'],
                    'id': track['id'],
                    'artists': [artist['name'] for artist in track.get('artists', [])],
                    'popularity': track.get('popularity', 0)
                })
        
        return common_tracks[:10]  # Return top 10 common tracks

# Utility functions for easy integration
def get_music_compatibility(user1, user2, time_range='long_term'):
    """Get music compatibility between two users"""
    algorithm = MusicMatchingAlgorithm()
    return algorithm.calculate_music_compatibility(user1, user2, time_range)

def find_top_music_matches(user, limit=10, time_range='long_term', min_score=50):
    """Find top music matches for a user"""
    User = get_user_model()
    algorithm = MusicMatchingAlgorithm()
    
    matches = []
    for other_user in User.objects.exclude(id=user.id).exclude(is_superuser=True):
        compatibility = algorithm.calculate_music_compatibility(user, other_user, time_range)
        if compatibility and compatibility['total_score'] >= min_score:
            matches.append({
                'user': other_user,
                'compatibility': compatibility
            })
    
    # Sort by total score and return top matches
    matches.sort(key=lambda x: x['compatibility']['total_score'], reverse=True)
    return matches[:limit]

def get_music_taste_summary(user, time_range='long_term'):
    """Get a summary of user's music taste"""
    algorithm = MusicMatchingAlgorithm()
    user_data = algorithm._get_user_music_data(user, time_range)
    
    if not user_data:
        return None
    
    # Analyze genres
    all_genres = []
    for artist in user_data['artists']:
        all_genres.extend(artist.get('genres', []))
    
    genre_counts = Counter(all_genres)
    top_genres = [{'genre': genre, 'count': count} for genre, count in genre_counts.most_common(10)]
    
    # Analyze artists
    top_artists = [{'name': artist['name'], 'popularity': artist.get('popularity', 0)} 
                   for artist in user_data['artists'][:10]]
    
    # Analyze tracks
    top_tracks = [{'name': track['name'], 'artists': [a['name'] for a in track.get('artists', [])], 
                   'popularity': track.get('popularity', 0)} for track in user_data['tracks'][:10]]
    
    return {
        'top_genres': top_genres,
        'top_artists': top_artists,
        'top_tracks': top_tracks,
        'total_artists': len(user_data['artists']),
        'total_tracks': len(user_data['tracks']),
        'time_range': time_range
    }
