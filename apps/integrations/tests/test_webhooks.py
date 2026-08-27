import pytest
from django.urls import reverse

from apps.integrations.models import OutboundReferralRequest, WebhookEvent

pytestmark = pytest.mark.django_db

WEBHOOK_SECRET = "test-webhook-secret"


@pytest.fixture
def outbound_request(referral):
    return OutboundReferralRequest.objects.create(
        referral=referral,
        external_hospital_code="EXT-01",
        payload={"reference_code": referral.reference_code},
        status=OutboundReferralRequest.Status.SENT,
    )


@pytest.fixture(autouse=True)
def _webhook_secret(settings):
    settings.EXTERNAL_HOSPITAL_WEBHOOK_SECRET = WEBHOOK_SECRET


class TestWebhookReceiveView:
    def test_rejects_requests_without_valid_secret(self, api_client, outbound_request):
        response = api_client.post(
            reverse("integration-webhook"),
            {"event_id": "evt-1", "outbound_request_id": outbound_request.id, "status": "ACCEPTED"},
        )
        assert response.status_code == 401

    def test_processes_a_valid_webhook_once(self, api_client, outbound_request):
        payload = {"event_id": "evt-2", "outbound_request_id": outbound_request.id, "status": "ACCEPTED"}
        response = api_client.post(reverse("integration-webhook"), payload, HTTP_X_WEBHOOK_SECRET=WEBHOOK_SECRET)

        assert response.status_code == 200
        assert response.data["status"] == "processed"
        event = WebhookEvent.objects.get(event_id="evt-2")
        assert event.processed is True

    def test_duplicate_event_id_is_ignored_on_replay(self, api_client, outbound_request):
        payload = {"event_id": "evt-3", "outbound_request_id": outbound_request.id, "status": "ACCEPTED"}
        first = api_client.post(reverse("integration-webhook"), payload, HTTP_X_WEBHOOK_SECRET=WEBHOOK_SECRET)
        second = api_client.post(reverse("integration-webhook"), payload, HTTP_X_WEBHOOK_SECRET=WEBHOOK_SECRET)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.data["status"] == "duplicate_ignored"
        assert WebhookEvent.objects.filter(event_id="evt-3").count() == 1

    def test_unknown_outbound_request_returns_404(self, api_client):
        payload = {"event_id": "evt-4", "outbound_request_id": 999999, "status": "ACCEPTED"}
        response = api_client.post(reverse("integration-webhook"), payload, HTTP_X_WEBHOOK_SECRET=WEBHOOK_SECRET)
        assert response.status_code == 404


class TestSimulatedHospitalReceiveView:
    def test_returns_acknowledgement_with_external_reference(self, api_client):
        response = api_client.post(
            reverse("simulated-hospital-receive"),
            {"reference_code": "RF-1", "priority": "URGENT", "reason_for_referral": "test"},
        )
        assert response.status_code == 201
        assert response.data["status"] == "ACKNOWLEDGED"
        assert response.data["external_reference"].startswith("EXT-")

    def test_force_failure_flag_simulates_an_outage(self, api_client):
        response = api_client.post(
            reverse("simulated-hospital-receive"),
            {"reference_code": "RF-1", "priority": "URGENT", "reason_for_referral": "test", "force_failure": True},
        )
        assert response.status_code == 503
