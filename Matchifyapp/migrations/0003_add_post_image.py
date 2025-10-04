from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Matchifyapp', '0002_create_post_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='image',
            field=models.FileField(blank=True, null=True, upload_to='post_images/'),
        ),
    ]
