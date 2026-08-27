import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.integrations.adapters import HospitalIntegrationError, get_hospital_integration_adapter
from apps.integrations.models import IntegrationLog, OutboundReferralRequest

logger = logging.getLogger("referralflow.integrations")


@shared_task(bind=True, max_retries=10)
def send_referral_to_external_hospital(self, outbound_request_id):
    """
    The retry ceiling actually enforced is `settings.EXTERNAL_HOSPITAL_MAX_RETRIES`,
    checked against the request's own attempt count below; the decorator's
    `max_retries=10` is only a hard safety net against runaway retries if
    that setting is ever misconfigured. Backoff is exponential so a
    struggling external system isn't hammered with retries.
    """
    try:
        outbound_request = OutboundReferralRequest.objects.select_related("referral").get(id=outbound_request_id)
    except OutboundReferralRequest.DoesNotExist:
        logger.warning("send_referral_to_external_hospital: request %s no longer exists", outbound_request_id)
        return

    outbound_request.attempt_count += 1
    outbound_request.last_attempted_at = timezone.now()
    outbound_request.status = OutboundReferralRequest.Status.SENT
    outbound_request.save(update_fields=["attempt_count", "last_attempted_at", "status"])

    adapter = get_hospital_integration_adapter()
    try:
        response = adapter.send_referral(outbound_request.payload)
    except HospitalIntegrationError as exc:
        IntegrationLog.objects.create(
            direction=IntegrationLog.Direction.OUTBOUND,
            level=IntegrationLog.Level.ERROR,
            message=str(exc),
            payload={"outbound_request_id": outbound_request.id, "attempt": outbound_request.attempt_count},
        )

        if outbound_request.attempt_count >= settings.EXTERNAL_HOSPITAL_MAX_RETRIES:
            outbound_request.status = OutboundReferralRequest.Status.FAILED
            outbound_request.save(update_fields=["status"])
            logger.error(
                "Giving up on outbound referral %s after %s attempts",
                outbound_request.id,
                outbound_request.attempt_count,
            )
            return

        backoff_seconds = 10 * (2 ** (outbound_request.attempt_count - 1))
        raise self.retry(exc=exc, countdown=backoff_seconds)

    outbound_request.status = OutboundReferralRequest.Status.ACKNOWLEDGED
    outbound_request.response_payload = response
    outbound_request.external_reference = response.get("external_reference", "")
    outbound_request.save(update_fields=["status", "response_payload", "external_reference"])

    IntegrationLog.objects.create(
        direction=IntegrationLog.Direction.OUTBOUND,
        level=IntegrationLog.Level.INFO,
        message="Referral acknowledged by external hospital",
        payload={
            "outbound_request_id": outbound_request.id,
            "external_reference": outbound_request.external_reference,
        },
    )
