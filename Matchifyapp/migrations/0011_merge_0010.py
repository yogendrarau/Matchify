"""Merge migration to resolve two conflicting 0010 migration heads.

This migration depends on both 0010 migrations and contains no operations.
It allows Django's migration graph to continue with a single head so `migrate`
can be run without conflict.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Matchifyapp", "0010_merge_0009"),
        ("Matchifyapp", "0010_alter_profile_image_message"),
    ]

    operations = []

