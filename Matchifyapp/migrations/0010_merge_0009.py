"""Merge migration to resolve two conflicting 0009 migration leaves.

This migration depends on both 0009 migrations and contains no operations.
It allows Django's migration graph to continue with a single head.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Matchifyapp", "0009_artistlisten_alter_profile_image_and_more"),
        ("Matchifyapp", "0009_profile_display_song_alter_profile_image_and_more"),
    ]

    operations = []
