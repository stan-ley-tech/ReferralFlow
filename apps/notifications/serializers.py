from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    referral_reference_code = serializers.CharField(source="referral.reference_code", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = (
            "id",
            "referral",
            "referral_reference_code",
            "notification_type",
            "channel",
            "title",
            "message",
            "is_read",
            "created_at",
            "sent_at",
        )
        read_only_fields = (
            "id",
            "referral",
            "referral_reference_code",
            "notification_type",
            "channel",
            "title",
            "message",
            "created_at",
            "sent_at",
        )
