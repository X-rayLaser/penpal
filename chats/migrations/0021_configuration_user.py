# Generated by Django 4.2.14 on 2024-08-23 09:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chats', '0020_systemmessage_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='configurations', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
