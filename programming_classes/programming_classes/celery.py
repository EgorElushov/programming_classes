import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'programming_classes.settings')

app = Celery('programming_classes')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
