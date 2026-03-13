import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myanimesite.settings')

app = Celery('myanimesite')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'update_actual_titles': {
        'task': 'services.tasks.update_actual_titles',
        'schedule': crontab(day_of_week='monday', hour=4, minute=0),
    },
    'update_all_titles': {
        'task': 'services.tasks.update_all_titles',
        'schedule': crontab(hour=5, minute=0),
    },
}
