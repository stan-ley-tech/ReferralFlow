import pytest
from django.urls import reverse

from tests.factories import HospitalFactory, PatientFactory

pytestmark = pytest.mark.django_db


class TestPatientVisibility:
    def test_doctor_only_sees_patients_registered_at_their_own_hospital(self, doctor_client, doctor, patient):
        other_hospital = HospitalFactory()
        other_patient = PatientFactory(registered_hospital=other_hospital)

        response = doctor_client.get(reverse("patient-list"))
        ids = {row["id"] for row in response.data["results"]}
        assert patient.id in ids
        assert other_patient.id not in ids

    def test_nurse_sees_patients_across_all_hospitals(self, db, patient):
        from apps.users.models import Role
        from tests.factories import UserFactory

        nurse = UserFactory(role=Role.NURSE)
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=nurse)

        other_hospital = HospitalFactory()
        other_patient = PatientFactory(registered_hospital=other_hospital)

        response = client.get(reverse("patient-list"))
        ids = {row["id"] for row in response.data["results"]}
        assert patient.id in ids
        assert other_patient.id in ids

    def test_patient_can_only_see_their_own_record(self, patient_client, patient):
        other_patient = PatientFactory()
        response = patient_client.get(reverse("patient-list"))
        ids = {row["id"] for row in response.data["results"]}
        assert patient.id in ids
        assert other_patient.id not in ids

    def test_patient_cannot_create_patient_records(self, patient_client):
        response = patient_client.post(
            reverse("patient-list"),
            {
                "medical_record_number": "MRN-NEW",
                "first_name": "New",
                "last_name": "Patient",
                "date_of_birth": "1995-05-05",
                "gender": "MALE",
                "registered_hospital": HospitalFactory().id,
            },
        )
        assert response.status_code == 403
