from django.conf import settings
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel
from apps.referrals.state_machine import ReferralStatus


class Priority(models.TextChoices):
    ROUTINE = "ROUTINE", "Routine"
    URGENT = "URGENT", "Urgent"
    EMERGENCY = "EMERGENCY", "Emergency"


class Referral(TimeStampedModel, SoftDeleteModel):
    reference_code = models.CharField(max_length=20, unique=True)

    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="referrals")
    referring_doctor = models.ForeignKey("hospitals.Doctor", on_delete=models.PROTECT, related_name="referrals_created")
    originating_hospital = models.ForeignKey(
        "hospitals.Hospital", on_delete=models.PROTECT, related_name="referrals_originated"
    )
    destination_hospital = models.ForeignKey(
        "hospitals.Hospital", on_delete=models.PROTECT, null=True, blank=True, related_name="referrals_received"
    )
    destination_department = models.ForeignKey(
        "hospitals.Department", on_delete=models.PROTECT, null=True, blank=True, related_name="referrals"
    )
    assigned_specialist = models.ForeignKey(
        "hospitals.Specialist",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="active_referrals",
    )

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.ROUTINE)
    status = models.CharField(max_length=20, choices=ReferralStatus.CHOICES, default=ReferralStatus.DRAFT, db_index=True)

    reason_for_referral = models.TextField()
    clinical_summary = models.TextField(blank=True)

    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    routed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="referrals_created"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["patient", "status"]),
            models.Index(fields=["originating_hospital", "status"]),
            models.Index(fields=["destination_hospital", "status"]),
            models.Index(fields=["assigned_specialist", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(priority__in=Priority.values),
                name="referral_priority_valid",
            ),
        ]

    def __str__(self):
        return f"{self.reference_code} ({self.status})"


class ReferralAssignment(TimeStampedModel):
    """
    Tracks every specialist a referral has been offered to, including
    rejections, so a coordinator can see the full routing history rather
    than only the most recent assignment.
    """

    class AssignmentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="assignments")
    specialist = models.ForeignKey("hospitals.Specialist", on_delete=models.PROTECT, related_name="referral_assignments")
    status = models.CharField(max_length=10, choices=AssignmentStatus.choices, default=AssignmentStatus.PENDING)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["referral", "status"]),
            models.Index(fields=["specialist", "status"]),
        ]

    def __str__(self):
        return f"{self.referral.reference_code} -> {self.specialist} ({self.status})"


class ReferralStatusHistory(models.Model):
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "Referral status histories"
        indexes = [
            models.Index(fields=["referral", "created_at"]),
        ]

    def __str__(self):
        return f"{self.referral_id}: {self.from_status or '-'} -> {self.to_status}"


class ClinicalNote(TimeStampedModel):
    class NoteType(models.TextChoices):
        GENERAL = "GENERAL", "General"
        DIAGNOSIS = "DIAGNOSIS", "Diagnosis"
        TREATMENT_PLAN = "TREATMENT_PLAN", "Treatment Plan"
        OUTCOME = "OUTCOME", "Outcome"

    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="clinical_notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="clinical_notes")
    note_type = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.GENERAL)
    content = models.TextField()

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["referral", "note_type"]),
        ]

    def __str__(self):
        return f"{self.note_type} note on {self.referral.reference_code}"


def referral_document_upload_path(instance, filename):
    return f"referrals/{instance.referral_id}/documents/{filename}"


class Document(TimeStampedModel):
    class DocumentType(models.TextChoices):
        LAB_RESULT = "LAB_RESULT", "Lab Result"
        IMAGING = "IMAGING", "Imaging"
        REFERRAL_LETTER = "REFERRAL_LETTER", "Referral Letter"
        OTHER = "OTHER", "Other"

    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="documents")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_documents")
    file = models.FileField(upload_to=referral_document_upload_path)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    original_filename = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["referral", "document_type"]),
        ]

    def __str__(self):
        return self.original_filename or self.file.name
