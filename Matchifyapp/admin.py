from django.contrib import admin
from .models import OtpToken, spotifyToken
from django.contrib.auth.admin import UserAdmin

# Register your models here.
@admin.register(spotifyToken)
class SpotifyTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "access_token", "token_type", "expires_in", "created_at")
    search_fields = ("user__username",)

@admin.register(OtpToken)
class OtpTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "otp_code", "otp_created_at", "otp_expires_at")
    search_fields = ("user__username",)