# Generated by Django 4.2.16 on 2024-09-13 11:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0022_remove_chat_human_chat_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='configuration',
            name='context_size',
        ),
        migrations.RemoveField(
            model_name='configuration',
            name='file_name',
        ),
        migrations.RemoveField(
            model_name='configuration',
            name='launch_params',
        ),
        migrations.RemoveField(
            model_name='configuration',
            name='model_repo',
        ),
    ]
