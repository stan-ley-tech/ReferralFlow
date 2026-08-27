import pytest
from rest_framework.test import APIClient

from apps.users.models import Role
from tests.factories import (
    DepartmentFactory,
    DoctorFactory,
    HospitalFactory,
    PatientFactory,
    ReferralFactory,
    SpecialistFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


def _authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def hospital(db):
    return HospitalFactory()


@pytest.fixture
def department(db, hospital):
    return DepartmentFactory(hospital=hospital)


@pytest.fixture
def admin_user(db):
    return UserFactory(role=Role.ADMIN, is_superuser=True, is_staff=True)


@pytest.fixture
def coordinator_user(db):
    return UserFactory(role=Role.REFERRAL_COORDINATOR)


@pytest.fixture
def doctor(db, hospital, department):
    return DoctorFactory(hospital=hospital, department=department)


@pytest.fixture
def specialist(db, hospital, department):
    return SpecialistFactory(hospital=hospital, department=department)


@pytest.fixture
def patient(db, hospital):
    return PatientFactory(registered_hospital=hospital)


@pytest.fixture
def referral(db, doctor, patient):
    return ReferralFactory(referring_doctor=doctor, patient=patient, originating_hospital=doctor.hospital)


@pytest.fixture
def doctor_client(doctor):
    return _authed_client(doctor.user)


@pytest.fixture
def specialist_client(specialist):
    return _authed_client(specialist.user)


@pytest.fixture
def admin_client(admin_user):
    return _authed_client(admin_user)


@pytest.fixture
def coordinator_client(coordinator_user):
    return _authed_client(coordinator_user)


@pytest.fixture
def patient_client(patient):
    patient.user = UserFactory(role=Role.PATIENT)
    patient.save(update_fields=["user"])
    return _authed_client(patient.user)
