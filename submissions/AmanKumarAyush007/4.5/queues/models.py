"""Tenant-scoped queue and waiting call persistence."""
from django.conf import settings
from django.db import models
from django.db.models import Q


class Tenant(models.Model):
    """Independent tenant scope for the standalone exercise."""
    name = models.CharField(max_length=120, unique=True)

    def __str__(self) -> str:
        return self.name


class TenantMembership(models.Model):
    """Explicit user membership, used to authorize every queue access."""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="queue_memberships")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("tenant", "user"), name="unique_queue_membership")]


class CallQueue(models.Model):
    """A bounded FIFO waiting queue belonging to exactly one tenant."""
    name = models.CharField(max_length=120)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="queues")
    max_size = models.PositiveIntegerField(default=50)
    current_calls = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("tenant", "name"), name="unique_tenant_queue_name"),
            models.CheckConstraint(
                check=Q(max_size__gte=1),
                name="queue_max_size_positive",
            )       
        ]


class QueuedCall(models.Model):
    """A call's queue entry and outcome, retaining history for statistics."""
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        SERVED = "served", "Served"
        ABANDONED = "abandoned", "Abandoned"

    queue = models.ForeignKey(CallQueue, on_delete=models.CASCADE, related_name="entries")
    call_id = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.WAITING)
    enqueued_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("queue", "call_id"), name="unique_queue_call_id")]
        indexes = [models.Index(fields=("queue", "status", "enqueued_at"))]
