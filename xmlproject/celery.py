import os
from celery import Celery

# Указываем Django настройки для celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmlproject.settings')

app = Celery('xmlproject')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Опционально: задача для отладки (можно удалить в боевом коде)
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')