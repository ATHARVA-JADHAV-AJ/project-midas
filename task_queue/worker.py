# Project Midas — Celery worker definition
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------

from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Single Celery app instance — imported by tasks.py and the CLI launcher.
# Keeping it in its own module avoids circular imports between tasks and consumer.
celery_app = Celery(
    "midas",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Acknowledge tasks only *after* completion, not on receipt.
    # If the worker crashes mid-task, the message stays in the broker
    # and will be redelivered — prevents silent task loss.
    task_acks_late=True,
    # Fetch one task at a time — model inference is serial because a single
    # GPU process cannot safely share VRAM across concurrent Celery threads.
    worker_prefetch_multiplier=1,
)

# Import tasks so Celery discovers and registers them at startup.
# The noqa comments suppress linter warnings about the import appearing
# after configuration — it must come last to avoid import-time circular deps.
from task_queue import tasks  # noqa: E402, F401
