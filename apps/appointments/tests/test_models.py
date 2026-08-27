import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.appointments.models import Appointment

pytestmark = pytest.mark.django_db


class TestAppointmentConstraints:
    def test_scheduled_end_must_be_after_start(self, referral, specialist, doctor):
        start = timezone.now()
        with pytest.raises(IntegrityError):
            Appointment.objects.create(
                referral=referral,
                specialist=specialist,
                scheduled_start=start,
                scheduled_end=start - timezone.timedelta(minutes=10),
                location="Room 1",
                created_by=doctor.user,
            )

    def test_valid_appointment_is_created(self, referral, specialist, doctor):
        start = timezone.now() + timezone.timedelta(days=1)
        appointment = Appointment.objects.create(
            referral=referral,
            specialist=specialist,
            scheduled_start=start,
            scheduled_end=start + timezone.timedelta(minutes=30),
            location="Room 1",
            created_by=doctor.user,
        )
        assert appointment.status == "SCHEDULED"
