import logging

from celery import shared_task

from apps.notifications.services import dispatch_referral_event

logger = logging.getLogger("referralflow.notifications")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_referral_notification(self, referral_id, event_type):
    """
    Runs outside the request/response cycle so a slow or failing
    notification channel never holds up the API call that triggered it.
    Retries on unexpected failures (e.g. a transient DB hiccup); a missing
    referral is not retried since that referral will never exist.
    """
    from apps.referrals.models import Referral

    try:
        referral = Referral.objects.select_related(
            "patient__user", "referring_doctor__user", "assigned_specialist__user"
        ).get(id=referral_id)
    except Referral.DoesNotExist:
        logger.warning("send_referral_notification: referral %s no longer exists", referral_id)
        return

    try:
        dispatch_referral_event(referral, event_type)
    except Exception as exc:
        logger.exception("Failed to dispatch notification for referral %s", referral_id)
        raise self.retry(exc=exc)
