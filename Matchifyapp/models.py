from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    # Profile image field for user avatars. Use db_column 'avatar' to match the
    # existing database column (some environments already have an 'avatar' column).
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True, db_column='avatar')
    # Optional JSON blob to store a small representation of the user's chosen display song
    # Example: {"id": "spotify:track:...", "name": "Song Name", "artist": "Artist", "album_art": "https://..."}
    display_song = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Profile({self.user.username})"

class OtpToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    otp_code = models.CharField(max_length=6)
    otp_created_at = models.DateTimeField(auto_now_add=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.user.username

class spotifyToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="spotify_tokens")
    created_at = models.DateTimeField(auto_now_add=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_in = models.DateTimeField()
    token_type = models.CharField(max_length=50)

    def __str__(self):
        return self.user.username

class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='friend_requests_sent', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='friend_requests_received', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')

class Friendship(models.Model):
    user1 = models.ForeignKey(User, related_name='friendships1', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='friendships2', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user1', 'user2')


class Post(models.Model):
    """Simple discussion post model."""
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    image = models.FileField(upload_to='post_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.author} at {self.created_at}"


class Comment(models.Model):
    """Comments attached to discussion posts."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author} on Post {self.post.id}"


class Reaction(models.Model):
    """User reaction to posts: like (1) or dislike (-1)."""
    LIKE = 1
    DISLIKE = -1

    VALUE_CHOICES = (
        (LIKE, 'Like'),
        (DISLIKE, 'Dislike'),
    )

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions', null=True, blank=True)
    # Allow reactions to target comments as well. Exactly one of (post, comment) should be set.
    comment = models.ForeignKey('Comment', on_delete=models.CASCADE, related_name='reactions', null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reactions')
    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure a user can react once per post or once per comment.
        unique_together = ('post', 'user')

    def __str__(self):
        return f"Reaction({self.user.username} -> {self.post.id}: {self.value})"


class ArtistListen(models.Model):
    """Aggregated listening time for a user for a specific artist.

    This model stores total milliseconds listened for a (user, artist) pair.
    A background job or management command should populate/update these rows by
    pulling users' recently-played history from Spotify and attributing track
    durations to their primary artist(s).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='artist_listens')
    artist_id = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    artist_name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    total_ms = models.BigIntegerField(default=0)  # total milliseconds listened
    play_count = models.IntegerField(default=0)  # number of times this artist appeared in recent-play history
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'artist_id')

    def minutes(self):
        return (self.total_ms or 0) / 60000.0

    def __str__(self):
        return f"ArtistListen(user={self.user.username} artist={self.artist_name} ms={self.total_ms})"


 