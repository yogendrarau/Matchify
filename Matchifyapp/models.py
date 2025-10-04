from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

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