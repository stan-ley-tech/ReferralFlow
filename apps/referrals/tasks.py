import logging

from celery import shared_task
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from apps.referrals.models import Referral
from apps.referrals.services.referral_service import ReferralService
from apps.referrals.state_machine import ReferralStatus

logger = logging.getLogger("referralflow.referrals")

DAILY_REPORT_CACHE_KEY_PREFIX = "referrals:daily_report"


@shared_task
def detect_expired_referrals():
    """
    Runs on a schedule (see config/celery.py) rather than in response to any
    single request, since expiry is a function of wall-clock time passing
    while a referral sits unaccepted - nothing about the referral itself
    changes to trigger it.
    """
    expired_candidates = Referral.objects.filter(
        status=ReferralStatus.ROUTED,
        expires_at__isnull=False,
        expires_at__lt=timezone.now(),
    )

    expired_count = 0
    for referral in expired_candidates:
        try:
            ReferralService.expire(referral=referral)
            expired_count += 1
        except Exception:
            logger.exception("Failed to expire referral %s", referral.reference_code)

    logger.info("detect_expired_referrals completed", extra={"expired_count": expired_count})
    return expired_count


@shared_task
def generate_daily_referral_report():
    """Summarizes yesterday's referral activity and caches it for the
    dashboard, since recomputing these aggregates on every request would be
    wasteful for a number that only changes once a day."""
    since = timezone.now() - timezone.timedelta(days=1)

    by_status = dict(
        Referral.objects.filter(created_at__gte=since).values_list("status").annotate(count=Count("id"))
    )
    by_priority = dict(
        Referral.objects.filter(created_at__gte=since).values_list("priority").annotate(count=Count("id"))
    )
    completed = Referral.objects.filter(completed_at__gte=since).count()
    expired = Referral.objects.filter(status=ReferralStatus.EXPIRED, updated_at__gte=since).count()

    report = {
        "generated_at": timezone.now().isoformat(),
        "window_start": since.isoformat(),
        "created_by_status": by_status,
        "created_by_priority": by_priority,
        "completed": completed,
        "expired": expired,
    }

    cache_key = f"{DAILY_REPORT_CACHE_KEY_PREFIX}:{timezone.now():%Y-%m-%d}"
    cache.set(cache_key, report, timeout=60 * 60 * 48)

    logger.info("generate_daily_referral_report completed", extra=report)
    return report


@shared_task
def process_uploaded_document(document_id):
    """
    Simulates post-upload processing (virus scanning, OCR, format
    validation) that a real deployment would hand off to a dedicated
    pipeline. Runs asynchronously so the upload request isn't held open
    waiting on work the client doesn't need to see the result of.
    """
    from apps.referrals.models import Document

    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.warning("process_uploaded_document: document %s no longer exists", document_id)
        return

    document.processed = True
    document.processed_at = timezone.now()
    document.save(update_fields=["processed", "processed_at"])
    logger.info("Document processed", extra={"document_id": document_id, "referral_id": document.referral_id})
