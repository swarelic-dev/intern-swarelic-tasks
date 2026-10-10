"""Atomic domain operations separated from HTTP and Celery."""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CallQueue, QueuedCall


@transaction.atomic
def enqueue_call(queue_id: int, call_id: str) -> tuple[QueuedCall, int]:
    """Admit one call if capacity exists, with a row lock on PostgreSQL."""
    queue = CallQueue.objects.select_for_update().get(pk=queue_id)
    if queue.current_calls >= queue.max_size:
        raise ValidationError({"detail": "Queue is full"})
    if QueuedCall.objects.filter(queue=queue, call_id=call_id).exists():
        raise ValidationError({"call_id": "Already submitted for this queue"})
    try:
        call = QueuedCall.objects.create(queue=queue, call_id=call_id)
    except IntegrityError as exc:
        raise ValidationError({"call_id": "Already submitted for this queue"}) from exc
    CallQueue.objects.filter(pk=queue.pk).update(current_calls=F("current_calls") + 1)
    return call, queue.current_calls + 1


@transaction.atomic
def dequeue_call(queue_id: int) -> QueuedCall | None:
    """Serve the oldest waiting call, preserving a historical record."""
    queue = CallQueue.objects.select_for_update().get(pk=queue_id)
    call = (QueuedCall.objects.filter(queue=queue, status=QueuedCall.Status.WAITING)
            .order_by("enqueued_at", "pk").first())
    if call is None:
        return None
    call.status = QueuedCall.Status.SERVED
    call.completed_at = timezone.now()
    call.save(update_fields=("status", "completed_at"))
    CallQueue.objects.filter(pk=queue.pk, current_calls__gt=0).update(current_calls=F("current_calls") - 1)
    return call
