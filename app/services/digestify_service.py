from celery import Celery
from app.core.celery_app import celery_app

@celery_app.task
def generate_digest(digest_id: str, topics: list[str]):
    print(f"Generating digest {digest_id} for topics: {topics}")
    return {"status": "completed", "digest_id": digest_id}