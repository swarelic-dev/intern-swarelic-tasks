"""Read and input contracts for call queue API."""
from rest_framework import serializers
from .models import CallQueue


class CallQueueSerializer(serializers.ModelSerializer):
    """Queue summary with current depth."""
    class Meta:
        model = CallQueue
        fields = ("id", "name", "tenant_id", "max_size", "current_calls")
        read_only_fields = fields


class EnqueueSerializer(serializers.Serializer):
    """Validate a new call identifier."""
    call_id = serializers.CharField(max_length=128, trim_whitespace=True, allow_blank=False)
