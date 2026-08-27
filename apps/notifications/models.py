from django.conf import settings
from django.db import models


class NotificationType(models.TextChoices):
    REFERRAL_ROUTED = "REFERRAL_ROUTED", "Referral Routed"
    REFERRAL_ACCEPTED = "REFERRAL_ACCEPTED", "Referral Accepted"
    REFERRAL_REJECTED = "REFERRAL_REJECTED", "Referral Rejected"
    REFERRAL_COMPLETED = "REFERRAL_COMPLETED", "Referral Completed"
    REFERRAL_CANCELLED = "REFERRAL_CANCELLED", "Referral Cancelled"
    REFERRAL_EXPIRED = "REFERRAL_EXPIRED", "Referral Expired"
    APPOINTMENT_SCHEDULED = "APPOINTMENT_SCHEDULED", "Appointment Scheduled"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER", "Appointment Reminder"


class NotificationChannel(models.TextChoices):
    IN_APP = "IN_APP", "In-App"
    EMAIL = "EMAIL", "Email"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    referral = models.ForeignKey(
        "referrals.Referral", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    channel = models.CharField(max_length=10, choices=NotificationChannel.choices, default=NotificationChannel.IN_APP)
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["referral", "notification_type"]),
        ]

    def __str__(self):
        return f"{self.notification_type} -> {self.recipient_id}"
