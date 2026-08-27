import pytest
from django.urls import reverse

from apps.referrals.models import Referral
from apps.referrals.state_machine import ReferralStatus
from tests.factories import DoctorFactory, PatientFactory, ReferralFactory

pytestmark = pytest.mark.django_db


class TestReferralCreate:
    def test_doctor_can_create_referral_for_themselves(self, doctor_client, doctor, patient):
        payload = {
            "patient": patient.id,
            "referring_doctor": doctor.id,
            "originating_hospital": doctor.hospital_id,
            "priority": "URGENT",
            "reason_for_referral": "Suspected arrhythmia",
        }
        response = doctor_client.post(reverse("referral-list"), payload)
        assert response.status_code == 201, response.data
        assert response.data["status"] == ReferralStatus.DRAFT
        assert Referral.objects.filter(reference_code=response.data["reference_code"]).exists()

    def test_doctor_cannot_create_referral_for_another_doctor(self, doctor_client, patient):
        other_doctor = DoctorFactory()
        payload = {
            "patient": patient.id,
            "referring_doctor": other_doctor.id,
            "originating_hospital": other_doctor.hospital_id,
            "priority": "ROUTINE",
            "reason_for_referral": "Test",
        }
        response = doctor_client.post(reverse("referral-list"), payload)
        assert response.status_code == 403

    def test_unauthenticated_request_is_rejected(self, api_client, doctor, patient):
        payload = {
            "patient": patient.id,
            "referring_doctor": doctor.id,
            "originating_hospital": doctor.hospital_id,
            "priority": "ROUTINE",
            "reason_for_referral": "Test",
        }
        response = api_client.post(reverse("referral-list"), payload)
        assert response.status_code == 401


class TestReferralVisibility:
    def test_doctor_only_sees_their_own_referrals(self, doctor_client, referral):
        other_referral = ReferralFactory()
        response = doctor_client.get(reverse("referral-list"))
        ids = {row["id"] for row in response.data["results"]}
        assert referral.id in ids
        assert other_referral.id not in ids

    def test_patient_only_sees_their_own_referral(self, patient_client, patient, referral):
        referral.patient = patient
        referral.save(update_fields=["patient"])
        other_referral = ReferralFactory()

        response = patient_client.get(reverse("referral-list"))
        ids = {row["id"] for row in response.data["results"]}
        assert referral.id in ids
        assert other_referral.id not in ids

    def test_doctor_cannot_retrieve_another_doctors_referral(self, doctor_client):
        other_referral = ReferralFactory()
        response = doctor_client.get(reverse("referral-detail", args=[other_referral.id]))
        assert response.status_code == 404


class TestReferralActions:
    def test_doctor_can_submit_but_not_route(self, doctor_client, referral, specialist):
        submit_url = reverse("referral-submit", args=[referral.id])
        assert doctor_client.post(submit_url).status_code == 200

        route_url = reverse("referral-route", args=[referral.id])
        route_response = doctor_client.post(route_url, {"specialist": specialist.id})
        assert route_response.status_code == 403  # doctors don't route; coordinators/admins do

    def test_only_assigned_specialist_can_accept(self, referral, specialist, coordinator_client, specialist_client):
        doctor_client_submit = coordinator_client
        doctor_client_submit.post(reverse("referral-submit", args=[referral.id]))
        doctor_client_submit.post(reverse("referral-route", args=[referral.id]), {"specialist": specialist.id})

        from tests.factories import SpecialistFactory

        other_specialist = SpecialistFactory()
        other_client = specialist_client.__class__()
        other_client.force_authenticate(user=other_specialist.user)

        # An unrelated specialist can't even see this referral, so the
        # queryset filters it out before the permission check runs -
        # a 404 rather than a 403, which avoids confirming its existence.
        forbidden_response = other_client.post(reverse("referral-accept", args=[referral.id]))
        assert forbidden_response.status_code == 404

        allowed_response = specialist_client.post(reverse("referral-accept", args=[referral.id]))
        assert allowed_response.status_code == 200
        referral.refresh_from_db()
        assert referral.status == ReferralStatus.ACCEPTED

    def test_invalid_transition_returns_409(self, coordinator_client, referral):
        # Coordinators bypass the assigned-specialist check, so this exercises
        # the state machine's own rejection of DRAFT -> ACCEPTED rather than
        # the permission layer.
        response = coordinator_client.post(reverse("referral-accept", args=[referral.id]))
        assert response.status_code == 409
