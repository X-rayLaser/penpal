import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.

development_mode = (os.environ.get('ENV') == 'DEV')
if development_mode:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.production_settings')

app = Celery('mysite')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


if development_mode:
    @app.task(bind=True, ignore_result=True)
    def debug_task(self):
        print(f'Request: {self.request!r}')