"""
Celery application configuration
"""
from celery import Celery
from config.settings import settings

# Create Celery app
app = Celery(
    'whatsapp_automation',
    broker=settings.celery_broker_url,
    backend=settings.redis_url
)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
)

# Auto-discover tasks
app.autodiscover_tasks(['src.core.tasks'])

if __name__ == '__main__':
    app.start() 