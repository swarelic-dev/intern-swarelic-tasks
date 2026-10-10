"""Call queue API routes."""
from django.urls import path
from .views import QueueListView, QueueStatsView, EnqueueView, DequeueView

urlpatterns = [
    path("queues/", QueueListView.as_view(), name="queues-list"),
    path("queues/<int:queue_id>/stats/", QueueStatsView.as_view(), name="queues-stats"),
    path("queues/<int:queue_id>/enqueue/", EnqueueView.as_view(), name="queues-enqueue"),
    path("queues/<int:queue_id>/dequeue/", DequeueView.as_view(), name="queues-dequeue"),
]
