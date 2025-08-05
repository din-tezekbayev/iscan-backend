from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "iscan",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
)