# Generated by Django 4.2.16 on 2024-09-19 12:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0023_remove_configuration_context_size_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='sandboxes',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
