# Generated by Django 4.2.6 on 2024-03-18 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0010_chat_date_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='file_name',
            field=models.CharField(default='', max_length=256),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='configuration',
            name='launch_params',
            field=models.JSONField(default={}),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='configuration',
            name='model_repo',
            field=models.CharField(default='', max_length=256),
            preserve_default=False,
        ),
    ]