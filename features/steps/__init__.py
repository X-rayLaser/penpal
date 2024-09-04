import os
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.test_settings'
django.setup()