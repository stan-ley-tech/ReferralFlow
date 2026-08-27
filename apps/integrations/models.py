from django.db import models

from apps.common.models import TimeStampedModel


class OutboundReferralRequest(TimeStampedModel):
    """
    Tracks one attempt to hand a referral to another hospital's system.
    Kept separate from the Referral itself since a single referral could,
    in principle, be re-sent after a failure without changing its own
    state machine.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        FAILED = "FAILED", "Failed"

    referral = models.ForeignKey("referrals.Referral", on_delete=models.CASCADE, related_name="outbound_requests")
    external_hospital_code = models.CharField(max_length=20)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING, db_index=True)
    payload = models.JSONField()
    response_payload = models.JSONField(null=True, blank=True)
    external_reference = models.CharField(max_length=50, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["referral", "status"]),
            models.Index(fields=["status", "last_attempted_at"]),
        ]

    def __str__(self):
        return f"{self.referral.reference_code} -> {self.external_hospital_code} ({self.status})"


class WebhookEvent(TimeStampedModel):
    """
    Every inbound webhook is recorded by its sender-provided event id before
    it's processed, so a retried delivery of the same event is recognized
    and skipped instead of being applied twice.
    """

    event_id = models.CharField(max_length=100, unique=True)
    source = models.CharField(max_length=50)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source", "processed"]),
        ]

    def __str__(self):
        return f"{self.source}:{self.event_id}"


class IntegrationLog(models.Model):
    class Direction(models.TextChoices):
        OUTBOUND = "OUTBOUND", "Outbound"
        INBOUND = "INBOUND", "Inbound"

    class Level(models.TextChoices):
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        ERROR = "ERROR", "Error"

    integration_name = models.CharField(max_length=50, default="external_hospital")
    direction = models.CharField(max_length=10, choices=Direction.choices)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    message = models.CharField(max_length=255)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["integration_name", "level", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.level}] {self.integration_name}: {self.message}"
