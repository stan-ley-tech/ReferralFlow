import pytest
from django.test import override_settings

from apps.integrations.adapters import HospitalIntegrationAdapter, HospitalIntegrationError
from apps.integrations.models import IntegrationLog, OutboundReferralRequest
from apps.integrations.services import initiate_outbound_referral
from apps.integrations.tasks import send_referral_to_external_hospital

pytestmark = pytest.mark.django_db


class _AlwaysSucceedsAdapter(HospitalIntegrationAdapter):
    def send_referral(self, payload):
        return {"status": "ACKNOWLEDGED", "external_reference": "EXT-STUB-1"}


class _AlwaysFailsAdapter(HospitalIntegrationAdapter):
    def send_referral(self, payload):
        raise HospitalIntegrationError("simulated outage", status_code=503)


class TestSendReferralToExternalHospital:
    def test_successful_send_marks_request_acknowledged(self, referral, monkeypatch):
        monkeypatch.setattr(
            "apps.integrations.tasks.get_hospital_integration_adapter", lambda: _AlwaysSucceedsAdapter()
        )
        outbound_request = OutboundReferralRequest.objects.create(
            referral=referral, external_hospital_code="EXT-01", payload={"reference_code": referral.reference_code}
        )

        send_referral_to_external_hospital(outbound_request.id)

        outbound_request.refresh_from_db()
        assert outbound_request.status == OutboundReferralRequest.Status.ACKNOWLEDGED
        assert outbound_request.external_reference == "EXT-STUB-1"
        assert outbound_request.attempt_count == 1
        assert IntegrationLog.objects.filter(direction=IntegrationLog.Direction.OUTBOUND, level=IntegrationLog.Level.INFO).exists()

    @override_settings(EXTERNAL_HOSPITAL_MAX_RETRIES=1)
    def test_exhausting_retries_marks_request_failed(self, referral, monkeypatch):
        monkeypatch.setattr(
            "apps.integrations.tasks.get_hospital_integration_adapter", lambda: _AlwaysFailsAdapter()
        )
        outbound_request = OutboundReferralRequest.objects.create(
            referral=referral, external_hospital_code="EXT-01", payload={"reference_code": referral.reference_code}
        )

        send_referral_to_external_hospital(outbound_request.id)

        outbound_request.refresh_from_db()
        assert outbound_request.status == OutboundReferralRequest.Status.FAILED
        assert outbound_request.attempt_count == 1
        assert IntegrationLog.objects.filter(direction=IntegrationLog.Direction.OUTBOUND, level=IntegrationLog.Level.ERROR).exists()

    def test_missing_outbound_request_is_a_no_op(self):
        send_referral_to_external_hospital(999999)


class TestInitiateOutboundReferral:
    def test_creates_pending_request_and_queues_task(self, referral, django_capture_on_commit_callbacks, monkeypatch):
        called_with = {}
        monkeypatch.setattr(
            "apps.integrations.tasks.send_referral_to_external_hospital.delay",
            lambda outbound_id: called_with.setdefault("id", outbound_id),
        )

        with django_capture_on_commit_callbacks(execute=True):
            outbound_request = initiate_outbound_referral(referral=referral, external_hospital_code="EXT-02")

        assert outbound_request.status == OutboundReferralRequest.Status.PENDING
        assert called_with["id"] == outbound_request.id
