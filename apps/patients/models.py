from django.conf import settings
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class Gender(models.TextChoices):
    FEMALE = "FEMALE", "Female"
    MALE = "MALE", "Male"
    OTHER = "OTHER", "Other"


class Patient(TimeStampedModel, SoftDeleteModel):
    """
    A patient record can exist without a linked user account - front-desk
    staff register patients who may never log in themselves - so `user` is
    optional and only set once the patient has portal access.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_profile",
    )
    medical_record_number = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    registered_hospital = models.ForeignKey(
        "hospitals.Hospital", on_delete=models.PROTECT, related_name="registered_patients"
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["registered_hospital", "is_deleted"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.medical_record_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
