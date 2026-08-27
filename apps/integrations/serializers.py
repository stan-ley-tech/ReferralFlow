from rest_framework import serializers

from apps.integrations.models import IntegrationLog, OutboundReferralRequest, WebhookEvent


class SimulatedReceiveSerializer(serializers.Serializer):
    """Validates the payload this project's own `SimulatedHospitalAdapter`
    sends to the simulated partner-hospital endpoint. `force_failure` lets
    tests exercise the retry path deterministically instead of relying on
    randomness."""

    reference_code = serializers.CharField()
    priority = serializers.CharField()
    reason_for_referral = serializers.CharField()
    force_failure = serializers.BooleanField(required=False, default=False)


class WebhookEventSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=100)
    outbound_request_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["ACKNOWLEDGED", "ACCEPTED", "REJECTED", "COMPLETED"])
    note = serializers.CharField(required=False, allow_blank=True, default="")


class OutboundReferralRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboundReferralRequest
        fields = (
            "id",
            "referral",
            "external_hospital_code",
            "status",
            "external_reference",
            "attempt_count",
            "last_attempted_at",
            "created_at",
        )
        read_only_fields = fields


class WebhookEventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = ("id", "event_id", "source", "processed", "processed_at", "created_at")
        read_only_fields = fields


class IntegrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationLog
        fields = ("id", "integration_name", "direction", "level", "message", "payload", "created_at")
        read_only_fields = fields
