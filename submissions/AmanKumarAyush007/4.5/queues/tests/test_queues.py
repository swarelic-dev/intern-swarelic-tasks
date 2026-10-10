"""HTTP and database contract tests for the isolated tenant-aware queue feature."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from queues.models import CallQueue, QueuedCall, Tenant, TenantMembership


class QueueAPITests(TestCase):
    """Verify authorization, capacity, FIFO, validation, and aggregate metrics."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="alice", password="password")
        self.outsider = get_user_model().objects.create_user(username="mallory", password="password")
        self.tenant = Tenant.objects.create(name="Alpha")
        self.other_tenant = Tenant.objects.create(name="Beta")
        TenantMembership.objects.create(tenant=self.tenant, user=self.user)
        self.queue = CallQueue.objects.create(tenant=self.tenant, name="support", max_size=2)
        self.other_queue = CallQueue.objects.create(tenant=self.other_tenant, name="support", max_size=2)
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def url(self, action, queue=None):
        return reverse("queues-" + action, args=([queue.pk if queue else self.queue.pk] if action != "list" else []))

    def test_requires_authentication(self):
        assert APIClient().get(self.url("list")).status_code in (401, 403)

    def test_list_queues_only_from_member_tenant(self):
        response = self.api.get(self.url("list"))
        assert response.status_code == 200
        assert [q["id"] for q in response.data] == [self.queue.pk]

    def test_nonmember_stats_return_404(self):
        assert self.api.get(self.url("stats", self.other_queue)).status_code == 404

    def test_nonmember_enqueue_return_404(self):
        assert self.api.post(self.url("enqueue", self.other_queue), {"call_id": "x"}).status_code == 404

    def test_nonmember_dequeue_return_404(self):
        assert self.api.post(self.url("dequeue", self.other_queue)).status_code == 404

    @patch("queues.views.alert_queue_threshold.delay")
    def test_enqueue_returns_201(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api.post(self.url("enqueue"), {"call_id": "call-1"})
        assert response.status_code == 201
        self.queue.refresh_from_db()
        assert self.queue.current_calls == 1
        delay.assert_called_once_with(self.queue.pk)

    @patch("queues.views.alert_queue_threshold.delay")
    def test_reject_duplicate_call(self, delay):
        self.api.post(self.url("enqueue"), {"call_id": "x"})
        assert self.api.post(self.url("enqueue"), {"call_id": "x"}).status_code == 400

    @patch("queues.views.alert_queue_threshold.delay")
    def test_queue_capacity(self, delay):
        for c in ("a", "b"):
            assert self.api.post(self.url("enqueue"), {"call_id": c}).status_code == 201
        assert self.api.post(self.url("enqueue"), {"call_id": "c"}).status_code == 400
        self.queue.refresh_from_db()
        assert self.queue.current_calls == 2

    @patch("queues.views.alert_queue_threshold.delay")
    def test_fifo_dequeue(self, delay):
        self.api.post(self.url("enqueue"), {"call_id": "a"})
        self.api.post(self.url("enqueue"), {"call_id": "b"})
        result = self.api.post(self.url("dequeue"))
        assert result.status_code == 200
        assert result.data["call_id"] == "a"
        self.queue.refresh_from_db()
        assert self.queue.current_calls == 1

    def test_empty_dequeue(self):
        assert self.api.post(self.url("dequeue")).status_code == 404

    def test_stats_empty(self):
        response = self.api.get(self.url("stats"))
        assert response.status_code == 200
        assert response.data["abandonment_rate"] == 0.0
        assert response.data["longest_wait_secs"] == 0.0

    @patch("queues.views.alert_queue_threshold.delay")
    def test_stats_nonempty(self, delay):
        self.api.post(self.url("enqueue"), {"call_id": "a"})
        data = self.api.get(self.url("stats")).data
        assert data["current_calls"] == 1
        assert data["longest_wait_secs"] >= 0

    def test_enqueue_validation(self):
        assert self.api.post(self.url("enqueue"), {"call_id": ""}).status_code == 400

    def test_outsider_cannot_list(self):
        self.api.force_authenticate(self.outsider)
        assert self.api.get(self.url("list")).data == []
