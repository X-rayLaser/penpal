# Generated by Django 4.2.6 on 2024-06-18 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0015_alter_chat_system_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/chat_images'),
        ),
    ]
