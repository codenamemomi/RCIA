from celery import Celery
from core.config import settings

celery_app = Celery(
    "rcia_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Auto-discover tasks in the api.v1.tasks module
celery_app.autodiscover_tasks(["api.v1.tasks"])
