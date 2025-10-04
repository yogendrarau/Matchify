# Generated repair migration: create Matchifyapp_post table if it doesn't exist
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('Matchifyapp', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS "Matchifyapp_post" (
                id bigserial PRIMARY KEY,
                content text NOT NULL,
                created_at timestamp with time zone NOT NULL DEFAULT now(),
                author_id bigint NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS Matchifyapp_post_author_id_idx ON "Matchifyapp_post" (author_id);
            """,
            reverse_sql="""
            DROP TABLE IF EXISTS "Matchifyapp_post" CASCADE;
            """,
        ),
    ]
