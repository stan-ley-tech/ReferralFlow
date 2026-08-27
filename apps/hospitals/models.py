from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Hospital(TimeStampedModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "city"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Department(TimeStampedModel):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["hospital__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["hospital", "code"], name="unique_department_code_per_hospital"),
        ]
        indexes = [
            models.Index(fields=["hospital", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.hospital.code}"


class Doctor(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_profile")
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="doctors")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="doctors")
    license_number = models.CharField(max_length=50, unique=True)
    specialization = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        indexes = [
            models.Index(fields=["hospital", "is_active"]),
        ]

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"


class Specialist(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="specialist_profile")
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="specialists")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="specialists")
    specialty = models.CharField(max_length=150)
    license_number = models.CharField(max_length=50, unique=True)
    is_accepting_referrals = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        indexes = [
            models.Index(fields=["hospital", "department", "is_accepting_referrals"]),
        ]

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username} ({self.specialty})"
