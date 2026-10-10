"""Tenant-authorized queue operations and analytics."""
from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, ExpressionWrapper, F, DurationField, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CallQueue, QueuedCall
from .serializers import CallQueueSerializer, EnqueueSerializer
from .services import enqueue_call, dequeue_call
from .tasks import alert_queue_threshold


def authorized_queues(user):
    """Restrict every read and mutation to an explicit tenant membership."""
    return CallQueue.objects.filter(tenant__memberships__user=user).distinct()


class QueueListView(APIView):
    """List queues visible to the authenticated tenant member."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return authorized queues with live depth."""
        return Response(CallQueueSerializer(authorized_queues(request.user), many=True).data)


class QueueStatsView(APIView):
    """Aggregate waiting times and abandoned/served outcomes."""
    permission_classes = [IsAuthenticated]

    def get(self, request, queue_id: int):
        """Return historical wait metrics and current longest wait in seconds."""
        queue = get_object_or_404(authorized_queues(request.user), pk=queue_id)
        entries = QueuedCall.objects.filter(queue=queue)
        finished = entries.exclude(completed_at__isnull=True).annotate(
            wait=ExpressionWrapper(F("completed_at") - F("enqueued_at"), output_field=DurationField()))
        average = finished.aggregate(value=Avg("wait"))["value"]
        oldest = entries.filter(status=QueuedCall.Status.WAITING).order_by("enqueued_at").first()
        total = entries.count()
        abandoned = entries.filter(status=QueuedCall.Status.ABANDONED).count()
        return Response({
            "queue_id": queue.pk, "current_calls": queue.current_calls,
            "avg_wait_time_secs": average.total_seconds() if average else 0.0,
            "longest_wait_secs": max(0.0, (timezone.now() - oldest.enqueued_at).total_seconds()) if oldest else 0.0,
            "abandonment_rate": abandoned / total if total else 0.0,
        })


class EnqueueView(APIView):
    """Admit a new waiting call without exceeding bounded capacity."""
    permission_classes = [IsAuthenticated]

    def post(self, request, queue_id: int):
        """Create a queue entry after validation and authorization."""
        queue = get_object_or_404(authorized_queues(request.user), pk=queue_id)
        serializer = EnqueueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        call, current = enqueue_call(queue.pk, serializer.validated_data["call_id"])
        transaction.on_commit(lambda: alert_queue_threshold.delay(queue.pk))
        return Response({"call_id": call.call_id, "current_calls": current}, status=status.HTTP_201_CREATED)


class DequeueView(APIView):
    """Serve the oldest waiting call in an authorized queue."""
    permission_classes = [IsAuthenticated]

    def post(self, request, queue_id: int):
        """Dequeue using a transaction and return 404 when empty."""
        queue = get_object_or_404(authorized_queues(request.user), pk=queue_id)
        call = dequeue_call(queue.pk)
        if call is None:
            return Response({"detail": "Queue is empty"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"call_id": call.call_id, "status": call.status})
