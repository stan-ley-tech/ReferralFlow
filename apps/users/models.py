from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    DOCTOR = "DOCTOR", "Doctor"
    SPECIALIST = "SPECIALIST", "Specialist"
    NURSE = "NURSE", "Nurse"
    REFERRAL_COORDINATOR = "REFERRAL_COORDINATOR", "Referral Coordinator"
    PATIENT = "PATIENT", "Patient"


class User(AbstractUser):
    """
    Extends Django's built-in user with the role that drives both RBAC
    checks and object-level permissions across the referral workflow.
    """

    role = models.CharField(max_length=32, choices=Role.choices, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def is_doctor(self):
        return self.role == Role.DOCTOR

    @property
    def is_specialist(self):
        return self.role == Role.SPECIALIST

    @property
    def is_nurse(self):
        return self.role == Role.NURSE

    @property
    def is_referral_coordinator(self):
        return self.role == Role.REFERRAL_COORDINATOR

    @property
    def is_patient_user(self):
        return self.role == Role.PATIENT
