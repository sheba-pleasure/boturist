from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')

app = Celery('web')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'process-scheduled-publications': {
        'task': 'admin_panel.tasks.process_scheduled_publications',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
    'update-campaign-metrics': {
        'task': 'admin_panel.tasks.update_campaign_metrics',
        'schedule': crontab(hour='*/1'),  # Run every hour
    },
    'process-post-requests': {
        'task': 'admin_panel.tasks.process_post_requests',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    }
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 