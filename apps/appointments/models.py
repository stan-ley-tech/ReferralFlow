from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class AppointmentStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    NO_SHOW = "NO_SHOW", "No Show"


class Appointment(TimeStampedModel):
    """
    A referral can accumulate more than one appointment over its lifetime
    if it gets rescheduled, so this is a plain foreign key rather than a
    one-to-one - `referral.appointments.latest('scheduled_start')` is the
    current one.
    """

    referral = models.ForeignKey("referrals.Referral", on_delete=models.CASCADE, related_name="appointments")
    specialist = models.ForeignKey("hospitals.Specialist", on_delete=models.PROTECT, related_name="appointments")
    status = models.CharField(max_length=15, choices=AppointmentStatus.choices, default=AppointmentStatus.SCHEDULED)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    location = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["scheduled_start"]
        indexes = [
            models.Index(fields=["specialist", "scheduled_start"]),
            models.Index(fields=["status", "scheduled_start"]),
            models.Index(fields=["referral", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(scheduled_end__gt=models.F("scheduled_start")),
                name="appointment_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.referral.reference_code} @ {self.scheduled_start:%Y-%m-%d %H:%M}"
