"""
Music Matching Algorithm for Matchify
Matches users based on their music taste (artists, tracks, genres).

This implementation ensures the reported compatibility score is symmetric
— the same value is returned for (A, B) and (B, A) by averaging the
directional metrics and producing stable "common" lists sorted by combined
rank/frequency so both sides see the same breakdown.
"""

from collections import Counter
from django.contrib.auth import get_user_model
from .models import spotifyToken
import requests
from .credentials import CLIENT_ID, CLIENT_SECRET
import logging

logger = logging.getLogger(__name__)


class MusicMatchingAlgorithm:
    """Core algorithm for matching users based on music taste."""

    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET

    def calculate_music_compatibility(self, user1, user2, time_range='long_term'):
        """Calculate symmetric music compatibility (0-100) and provide breakdowns.

        The returned dict has keys: total_score, breakdown, common_artists,
        common_genres, common_tracks. The total_score is calibrated and the
        same regardless of argument order.
        """
        try:
            user1_data = self._get_user_music_data(user1, time_range)
            user2_data = self._get_user_music_data(user2, time_range)

            if user1_data and user2_data:
                # directional scores (A vs B) and (B vs A)
                a_artist = self._calculate_artist_compatibility(user1_data, user2_data)
                b_artist = self._calculate_artist_compatibility(user2_data, user1_data)
                artist_score = (a_artist + b_artist) / 2.0

                a_genre = self._calculate_genre_compatibility(user1_data, user2_data)
                b_genre = self._calculate_genre_compatibility(user2_data, user1_data)
                genre_score = (a_genre + b_genre) / 2.0

                a_track = self._calculate_track_compatibility(user1_data, user2_data)
                b_track = self._calculate_track_compatibility(user2_data, user1_data)
                track_score = (a_track + b_track) / 2.0

                weights = {'artist': 0.45, 'genre': 0.30, 'track': 0.25}
                total_score = (
                    artist_score * weights['artist'] +
                    genre_score * weights['genre'] +
                    track_score * weights['track']
                )

                # produce merged common lists that are stable and symmetric
                common_artists = self._merge_common_artists(user1_data, user2_data)
                common_tracks = self._merge_common_tracks(user1_data, user2_data)
                common_genres = self._merge_common_genres(user1_data, user2_data)

                return self._finalize_result(
                    raw_total=total_score,
                    breakdown={
                        'artist_compatibility': round(artist_score, 1),
                        'genre_compatibility': round(genre_score, 1),
                        'track_compatibility': round(track_score, 1)
                    },
                    common_artists=common_artists,
                    common_genres=common_genres,
                    common_tracks=common_tracks
                )

            # Fallback: use ranking/overlap approach when API data is unavailable
            logger.debug('Falling back to ranking-overlap compatibility')
            from .views import get_top_artists

            u1_art = get_top_artists(user1, time_range) if get_top_artists else []
            u2_art = get_top_artists(user2, time_range) if get_top_artists else []

            def normalize_artists(artists):
                out = []
                if isinstance(artists, dict) and artists.get('Error'):
                    return out
                for i, a in enumerate(artists[:50]):
                    aid = a.get('id') if isinstance(a, dict) else None
                    name = a.get('name') if isinstance(a, dict) else str(a)
                    genres = a.get('genres', []) if isinstance(a, dict) else []
                    out.append({'id': aid, 'name': name, 'genres': genres, 'rank': i + 1})
                return out

            na1 = normalize_artists(u1_art)
            na2 = normalize_artists(u2_art)

            rank1 = {a['id']: a['rank'] for a in na1 if a['id']}
            rank2 = {a['id']: a['rank'] for a in na2 if a['id']}

            def rank_weight(rank):
                return max(0.02, (51 - rank) / 51)

            # directional artist scores then average
            def directional_artist_score(na_from, rank_to):
                numer = 0.0
                denom = 0.0
                for a in na_from:
                    if a['id']:
                        w = rank_weight(a['rank'])
                        denom += w
                        if a['id'] in rank_to:
                            numer += w * rank_weight(rank_to[a['id']])
                return (numer / denom * 100.0) if denom > 0 else 0.0

            artist_score = (directional_artist_score(na1, rank2) + directional_artist_score(na2, rank1)) / 2.0

            # tracks (try API) — compute directional and average
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

            def directional_track_score(from_tracks, to_tracks):
                if not from_tracks:
                    return 0.0
                common = set(from_tracks) & set(to_tracks)
                numer = 0.0
                denom = 0.0
                for i, tid in enumerate(from_tracks[:50]):
                    w = rank_weight(i + 1)
                    denom += w
                    if tid in common:
                        j = to_tracks.index(tid)
                        numer += w * rank_weight(j + 1)
                return (numer / denom * 100.0) if denom > 0 else 0.0

            track_score = (directional_track_score(u1_tracks, u2_tracks) + directional_track_score(u2_tracks, u1_tracks)) / 2.0

            # genres via normalized artists
            g1 = set(g for a in na1 for g in a.get('genres', []))
            g2 = set(g for a in na2 for g in a.get('genres', []))
            inter = len(g1 & g2)
            union = len(g1 | g2)
            genre_score_raw = (inter / union * 100.0) if union > 0 else 0.0
            # symmetry: same either way, but keep averaging pattern for consistency
            genre_score = genre_score_raw

            weights = {'artist': 0.45, 'genre': 0.30, 'track': 0.25}
            total = artist_score * weights['artist'] + genre_score * weights['genre'] + track_score * weights['track']

            common_artists = self._merge_common_artists_from_normalized(na1, na2)
            common_tracks = list(set(u1_tracks) & set(u2_tracks))[:10]
            common_genres = list(g1 & g2)[:10]

            return self._finalize_result(
                raw_total=min(100.0, total),
                breakdown={
                    'artist_compatibility': round(artist_score, 1),
                    'genre_compatibility': round(genre_score, 1),
                    'track_compatibility': round(track_score, 1)
                },
                common_artists=common_artists,
                common_genres=common_genres,
                common_tracks=common_tracks
            )
        except Exception as e:
            logger.error(f"Error calculating music compatibility: {e}")
            return None

    def _get_user_music_data(self, user, time_range):
        """Get comprehensive music data for a user from Spotify API."""
        try:
            from .views import get_token, get_auth_header

            token = get_token(user)
            if not token:
                return None

            headers = get_auth_header(user)
            if not headers:
                return None

            artists_url = "https://api.spotify.com/v1/me/top/artists"
            artists_response = requests.get(artists_url, headers=headers, params={
                'time_range': time_range,
                'limit': 50
            })

            if artists_response.status_code != 200:
                return None

            artists_data = artists_response.json().get('items', [])

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
        """Directional artist-based compatibility (0-100) from user1 -> user2."""
        user1_artists = {artist['id']: artist for artist in user1_data['artists'] if artist.get('id')}
        user2_artists = {artist['id']: artist for artist in user2_data['artists'] if artist.get('id')}

        common = set(user1_artists.keys()) & set(user2_artists.keys())
        if not common:
            return 0

        total_score = 0.0
        max_possible = 0.0
        for i, artist in enumerate(user1_data['artists']):
            aid = artist.get('id')
            if not aid:
                continue
            weight = 1.0 / (i + 1)
            max_possible += weight
            if aid in common:
                user2_rank = next((j for j, a in enumerate(user2_data['artists']) if a.get('id') == aid), 50)
                rank_penalty = 1.0 / (abs(i - user2_rank) + 1)
                total_score += weight * rank_penalty

        return min(100.0, (total_score / max_possible) * 100.0) if max_possible > 0 else 0.0

    def _calculate_genre_compatibility(self, user1_data, user2_data):
        """Directional genre compatibility (0-100)."""
        user1_genres = []
        for artist in user1_data['artists']:
            user1_genres.extend(artist.get('genres', []))

        user2_genres = []
        for artist in user2_data['artists']:
            user2_genres.extend(artist.get('genres', []))

        if not user1_genres or not user2_genres:
            return 0.0

        s1 = set(user1_genres)
        s2 = set(user2_genres)
        inter = len(s1 & s2)
        union = len(s1 | s2)
        jaccard = (inter / union) if union > 0 else 0.0

        c1 = Counter(user1_genres)
        c2 = Counter(user2_genres)
        weighted = 0.0
        total_w = 0.0
        for g in s1 & s2:
            w = c1[g] + c2[g]
            weighted += w
            total_w += w
        freq_score = (weighted / total_w) if total_w > 0 else 0.0

        final = (jaccard * 0.6 + freq_score * 0.4) * 100.0
        return min(100.0, final)

    def _calculate_track_compatibility(self, user1_data, user2_data):
        """Directional track compatibility (0-100) from user1 -> user2."""
        user1_tracks = [t.get('id') for t in user1_data['tracks'] if t.get('id')]
        user2_tracks = [t.get('id') for t in user2_data['tracks'] if t.get('id')]

        common = set(user1_tracks) & set(user2_tracks)
        if not common:
            return 0.0

        total = 0.0
        max_possible = 0.0
        for i, tid in enumerate(user1_tracks):
            weight = 1.0 / (i + 1)
            max_possible += weight
            if tid in common:
                j = user2_tracks.index(tid)
                rank_penalty = 1.0 / (abs(i - j) + 1)
                total += weight * rank_penalty

        return min(100.0, (total / max_possible) * 100.0) if max_possible > 0 else 0.0

    # --- Common-list merging helpers (produce symmetric, stable lists)
    def _merge_common_artists(self, u1_data, u2_data, limit=10):
        """Return merged list of common artists sorted by combined rank."""
        u1_map = {a.get('id'): (i + 1, a) for i, a in enumerate(u1_data['artists']) if a.get('id')}
        u2_map = {a.get('id'): (i + 1, a) for i, a in enumerate(u2_data['artists']) if a.get('id')}

        common_ids = set(u1_map.keys()) & set(u2_map.keys())
        merged = []
        for aid in common_ids:
            r1, a1 = u1_map.get(aid, (999, None))
            r2, a2 = u2_map.get(aid, (999, None))
            rank_sum = (r1 or 999) + (r2 or 999)
            # prefer artist info from u1 then u2
            info = a1 if a1 else a2
            merged.append((rank_sum, info))

        merged.sort(key=lambda x: x[0])
        out = []
        for _, artist in merged[:limit]:
            out.append({
                'name': artist.get('name'),
                'id': artist.get('id'),
                'genres': artist.get('genres', []),
                'popularity': artist.get('popularity', 0)
            })
        return out

    def _merge_common_tracks(self, u1_data, u2_data, limit=10):
        """Return merged list of common tracks sorted by combined rank."""
        u1_map = {t.get('id'): (i + 1, t) for i, t in enumerate(u1_data['tracks']) if t.get('id')}
        u2_map = {t.get('id'): (i + 1, t) for i, t in enumerate(u2_data['tracks']) if t.get('id')}

        common_ids = set(u1_map.keys()) & set(u2_map.keys())
        merged = []
        for tid in common_ids:
            r1, t1 = u1_map.get(tid, (999, None))
            r2, t2 = u2_map.get(tid, (999, None))
            rank_sum = (r1 or 999) + (r2 or 999)
            info = t1 if t1 else t2
            merged.append((rank_sum, info))

        merged.sort(key=lambda x: x[0])
        out = []
        for _, track in merged[:limit]:
            out.append({
                'name': track.get('name'),
                'id': track.get('id'),
                'artists': [a.get('name') for a in track.get('artists', [])],
                'popularity': track.get('popularity', 0)
            })
        return out

    def _merge_common_genres(self, u1_data, u2_data, limit=10):
        """Return top common genres sorted by combined frequency."""
        g1 = []
        for a in u1_data['artists']:
            g1.extend(a.get('genres', []))
        g2 = []
        for a in u2_data['artists']:
            g2.extend(a.get('genres', []))

        c1 = Counter(g1)
        c2 = Counter(g2)
        common = set(c1.keys()) & set(c2.keys())
        merged = []
        for g in common:
            merged.append((c1[g] + c2[g], g))
        merged.sort(key=lambda x: x[0], reverse=True)
        return [g for _, g in merged[:limit]]

    # helper used in fallback to merge normalized artist lists
    def _merge_common_artists_from_normalized(self, na1, na2, limit=10):
        id_to_rank1 = {a['id']: a['rank'] for a in na1 if a.get('id')}
        id_to_rank2 = {a['id']: a['rank'] for a in na2 if a.get('id')}
        common = set(id_to_rank1.keys()) & set(id_to_rank2.keys())
        merged = []
        for aid in common:
            merged.append((id_to_rank1.get(aid, 999) + id_to_rank2.get(aid, 999), aid))
        merged.sort(key=lambda x: x[0])
        return [aid for _, aid in merged[:limit]]

    # --- Calibration helpers (unchanged) ---
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
                # Finalize and calibrate scores to the app-wide distribution
                return self._finalize_result(
                    raw_total=total_score,
                    breakdown={
                        'artist_compatibility': round(artist_score, 1),
                        'genre_compatibility': round(genre_score, 1),
                        'track_compatibility': round(track_score, 1)
                    },
                    common_artists=self._get_common_artists(user1_data, user2_data),
                    common_genres=self._get_common_genres(user1_data, user2_data),
                    common_tracks=self._get_common_tracks(user1_data, user2_data)
                )

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

            # Finalize and calibrate fallback scores as well
            return self._finalize_result(
                raw_total=min(100.0, total),
                breakdown={
                    'artist_compatibility': round(artist_score, 1),
                    'genre_compatibility': round(genre_score, 1),
                    'track_compatibility': round(track_score, 1)
                },
                common_artists=list(common)[:10],
                common_genres=list(g1 & g2)[:10],
                common_tracks=list(common_tracks)[:10]
            )
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

    # --- Calibration helpers ---
    def _map_to_target_distribution(self, raw_score):
        """
        Map a raw score (0-100) to a calibrated score so that overall distribution
        roughly matches the desired buckets the user requested.

        The mapping is deterministic and monotonic. It remaps quantiles from the
        raw_score into the target bucket ranges.
        """
        # Ensure bounds
        s = max(0.0, min(100.0, float(raw_score)))

        # Define target CDF bucket endpoints and mapped score ranges.
        # The user requested approximate distribution across these bands:
        # 90-100: 10%, 80-90: 20%, 70-80: 35%, 60-70: 15%, 50-60: 10%, 40-50: 6%, rest evenly.
        # We'll create a piecewise linear mapping from raw percentiles to these bands.

        # Build cumulative distribution thresholds (percentiles)
        buckets = [
            (90, 100, 0.10),
            (80, 90, 0.20),
            (70, 80, 0.35),
            (60, 70, 0.15),
            (50, 60, 0.10),
            (40, 50, 0.06),
            (0, 40, 0.04)  # remainder (4%) across 0-40
        ]

        # Precompute cumulative mass and target percentile edges
        cum = 0.0
        segments = []  # list of (src_low, src_high, tgt_low, tgt_high)
        src_low = 0.0
        for low, high, mass in reversed(buckets):
            # We'll map the source percentile slice proportionally within 0-100 by mass.
            src_high = src_low + mass * 100.0
            # target is the numeric score range [low, high]
            segments.append((src_low, src_high, float(low), float(high)))
            src_low = src_high

        # segments were built from low to high in reversed order; ensure monotonic
        segments.sort(key=lambda x: x[0])

        # Interpret raw_score as a percentile of 'raw' distribution (approx):
        # Since we don't have the raw distribution, assume raw_score itself is percentile.
        p = s

        for src_lo, src_hi, tgt_lo, tgt_hi in segments:
            if p >= src_lo and (p <= src_hi or src_hi == src_lo):
                # local fraction inside this segment
                span = (src_hi - src_lo) if (src_hi - src_lo) > 0 else 1.0
                frac = (p - src_lo) / span
                mapped = tgt_lo + frac * (tgt_hi - tgt_lo)
                return max(0.0, min(100.0, mapped))

        # fallback
        return s

    def _finalize_result(self, raw_total, breakdown, common_artists, common_genres, common_tracks):
        """
        Apply calibration to the total score and scale breakdown values proportionally.
        Returns the final dict expected by callers.
        """
        try:
            # raw_total is expected in 0-100; calibrate it
            calibrated = self._map_to_target_distribution(raw_total)

            # If raw_total is 0 or negative, map it to a minimal positive percentile
            # so it's extremely unlikely to produce a zero compatibility.
            if raw_total <= 0:
                calibrated = self._map_to_target_distribution(1.0)
                # If breakdown values are all zero, distribute calibrated by default weights
                raw_vals = [max(0.0, float(v)) for _, v in breakdown.items()]
                raw_sum = sum(raw_vals)
                if raw_sum <= 0:
                    # default weights aligned with main algorithm
                    default_weights = {'artist_compatibility': 0.45, 'genre_compatibility': 0.30, 'track_compatibility': 0.25}
                    final_breakdown = {k: round(calibrated * w, 1) for k, w in default_weights.items()}
                else:
                    scale = calibrated / raw_sum
                    final_breakdown = {k: round(max(0.0, float(v) * scale), 1) for k, v in breakdown.items()}
            else:
                # Scale individual components so they sum approximately to calibrated total
                # Compute current sum of breakdown weights
                parts = list(breakdown.items())
                raw_vals = [max(0.0, float(v)) for _, v in parts]
                raw_sum = sum(raw_vals)
                if raw_sum <= 0:
                    final_breakdown = {k: float(v) for k, v in breakdown.items()}
                else:
                    scale = calibrated / raw_sum
                    final_breakdown = {k: round(max(0.0, float(v) * scale), 1) for k, v in breakdown.items()}

            return {
                'total_score': round(float(calibrated), 1),
                'breakdown': final_breakdown,
                'common_artists': common_artists,
                'common_genres': common_genres,
                'common_tracks': common_tracks
            }
        except Exception as e:
            logger.error(f"Error finalizing compatibility result: {e}")
            # fallback to uncalibrated
            return {
                'total_score': round(float(raw_total), 1),
                'breakdown': breakdown,
                'common_artists': common_artists,
                'common_genres': common_genres,
                'common_tracks': common_tracks
            }

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
