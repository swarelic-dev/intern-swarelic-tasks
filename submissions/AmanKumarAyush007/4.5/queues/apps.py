from django.apps import AppConfig


class QueuesConfig(AppConfig):
    """Queue application registration."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "queues"
