from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, default=None)
    content_type_name = serializers.CharField(source="content_type.model", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "action",
            "actor",
            "actor_username",
            "content_type_name",
            "object_id",
            "metadata",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields
