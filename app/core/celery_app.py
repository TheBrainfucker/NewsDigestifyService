from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "digestify",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    include=['app.services.digestify_service']
)

# Tasks will be auto-discovered via the include configuration
