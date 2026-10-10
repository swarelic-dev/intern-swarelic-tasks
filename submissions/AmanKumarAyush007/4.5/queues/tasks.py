"""Asynchronous queue depth alert; replace logging with your alert provider."""
import logging
from celery import shared_task
from django.conf import settings
from .models import CallQueue

logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def alert_queue_threshold(queue_id: int) -> None:
    """Log a structured alert if the queue depth exceeds configured threshold."""
    try:
        queue = CallQueue.objects.get(pk=queue_id)
    except CallQueue.DoesNotExist:
        logger.warning("queue_alert_missing_queue", extra={"queue_id": queue_id})
        return
    if queue.current_calls > settings.QUEUE_ALERT_THRESHOLD:
        logger.warning("queue_threshold_exceeded", extra={
            "queue_id": queue.pk, "tenant_id": queue.tenant_id, "current_calls": queue.current_calls,
        })
