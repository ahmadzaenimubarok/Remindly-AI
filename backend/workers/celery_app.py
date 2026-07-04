from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "reseller_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "workers.discovery_worker",
        "workers.content_worker",
        "workers.engagement_worker",
        "workers.conversion_worker",
        "workers.lead_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "workers.discovery_worker.*": {"queue": "discovery"},
        "workers.content_worker.*": {"queue": "content"},
        "workers.engagement_worker.*": {"queue": "engagement"},
        "workers.conversion_worker.*": {"queue": "conversion"},
        "workers.lead_worker.*": {"queue": "leads"},
    },
    beat_schedule={
        "decay-leads-daily": {
            "task": "workers.lead_worker.decay_leads",
            "schedule": 86400,  # setiap 24 jam
        },
    },
)
