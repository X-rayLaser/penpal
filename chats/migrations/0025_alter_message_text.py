# Generated by Django 4.2.16 on 2024-09-21 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0024_configuration_sandboxes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='text',
            field=models.CharField(max_length=8000),
        ),
    ]