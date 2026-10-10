# Generated manually for the isolated exercise; run makemigrations --check before submission.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Tenant", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=120, unique=True)),
        ]),
        migrations.CreateModel(name="CallQueue", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=120)),
            ("max_size", models.PositiveIntegerField(default=50)),
            ("current_calls", models.PositiveIntegerField(default=0)),
            ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="queues", to="queues.tenant")),
        ], options={"constraints": [
            models.UniqueConstraint(fields=("tenant", "name"), name="unique_tenant_queue_name"),
            models.CheckConstraint(check=models.Q(max_size__gte=1), name="queue_max_size_positive"),
        ]}),
        migrations.CreateModel(name="TenantMembership", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="queues.tenant")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="queue_memberships", to=settings.AUTH_USER_MODEL)),
        ], options={"constraints": [models.UniqueConstraint(fields=("tenant", "user"), name="unique_queue_membership")]}),
        migrations.CreateModel(name="QueuedCall", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("call_id", models.CharField(max_length=128)),
            ("status", models.CharField(choices=[("waiting", "Waiting"), ("served", "Served"), ("abandoned", "Abandoned")], default="waiting", max_length=16)),
            ("enqueued_at", models.DateTimeField(auto_now_add=True)),
            ("completed_at", models.DateTimeField(blank=True, null=True)),
            ("queue", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entries", to="queues.callqueue")),
        ], options={"constraints": [models.UniqueConstraint(fields=("queue", "call_id"), name="unique_queue_call_id")],
            "indexes": [models.Index(fields=["queue", "status", "enqueued_at"], name="queues_queu_queue_i_da609e_idx")]}),
    ]
