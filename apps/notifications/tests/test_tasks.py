import pytest

from apps.notifications.models import Notification
from apps.notifications.tasks import send_referral_notification

pytestmark = pytest.mark.django_db


class TestSendReferralNotificationTask:
    def test_task_creates_notification_for_recipient(self, referral, specialist):
        from apps.referrals.services.referral_service import ReferralService

        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        referral = ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)

        # ReferralService.route already queues this via transaction.on_commit,
        # which pytest-django's autouse `db` fixture doesn't fire outside a
        # real transaction boundary, so call it directly to test the task in
        # isolation.
        Notification.objects.filter(referral=referral).delete()
        send_referral_notification(referral.id, "REFERRAL_ROUTED")

        assert Notification.objects.filter(referral=referral, recipient=specialist.user).exists()

    def test_task_is_a_no_op_for_a_missing_referral(self):
        # Should log and return rather than raising.
        send_referral_notification(999999, "REFERRAL_ROUTED")
