import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meal_planner_service.settings')

app = Celery('meal_planner_service')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
