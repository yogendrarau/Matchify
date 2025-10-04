from django.urls import path
from . import views
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.home, name = "home"),
    path("register", views.register, name = "register"),
    path("login", views.login, name = "login"),
    path("logout", views.logout, name = "logout"),
    path("verify-email/<slug:username>", views.verify_email, name="verify_email"),
    path("resend-otp", views.resend_otp, name="resend_otp"),
    path("auth-url", AuthenticationURL.as_view(), name="auth-url"),
    path("redirect/", views.spotify_redirect, name="redirect"),
    path("check-auth", CheckAuthentication.as_view(), name="check-auth"),
    path("success", views.success, name="success"),
    path("top-artists", views.top_artists, name="top_artists"),
    path("mapify", views.mapify, name="mapify"),
    path("send-friend-request/<str:username>", views.send_friend_request, name="send_friend_request"),
    path("accept-friend-request/<str:username>", views.accept_friend_request, name="accept_friend_request"),
    path("reject-friend-request/<str:username>", views.reject_friend_request, name="reject_friend_request"),
    path("remove-friend/<str:username>", views.remove_friend, name="remove_friend"),
    path("get-current-track", views.get_current_track_endpoint, name="get_current_track"),
    path("api/connections", views.get_connections, name="get_connections"),
    path("profile/<str:username>/", views.profile, name="profile"),
    path("api/all_users", views.get_all_users, name="all_users"),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('api/pending_requests', views.pending_requests, name='pending_requests'),
]