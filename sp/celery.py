import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sp.settings")

app = Celery("sp")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()  # this is what finds tasks.py inside each installed app automatically

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
