"""
Celery configuration for citis project.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'citis.settings')

app = Celery('citis')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'archive.tasks.archive_url_task': {'queue': 'archive'},
        'archive.tasks.extract_assets_task': {'queue': 'assets'},
        'archive.tasks.update_visit_analytics_task': {'queue': 'analytics'},
    },
    
    # Retry configuration
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Result backend configuration
    result_expires=3600,  # 1 hour
) 