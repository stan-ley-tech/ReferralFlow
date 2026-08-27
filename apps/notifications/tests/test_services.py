import pytest

from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import dispatch_referral_event
from apps.referrals.services.referral_service import ReferralService
from apps.users.models import Role
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestDispatchReferralEvent:
    def test_routed_event_notifies_only_the_specialist(self, referral, specialist, django_capture_on_commit_callbacks):
        # ReferralService.route() queues the notification via
        # transaction.on_commit, which never fires under the default
        # rollback-based db fixture unless captured explicitly.
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        with django_capture_on_commit_callbacks(execute=True):
            referral = ReferralService.route(
                referral=referral, specialist=specialist, actor=referral.referring_doctor.user
            )

        notifications = Notification.objects.filter(
            referral=referral, notification_type=NotificationType.REFERRAL_ROUTED
        )
        recipients = set(notifications.values_list("recipient_id", flat=True))
        assert recipients == {specialist.user_id}

    def test_accepted_event_notifies_both_doctor_and_patient(self, referral):
        referral.patient.user = UserFactory(role=Role.PATIENT)
        referral.patient.save(update_fields=["user"])

        dispatch_referral_event(referral, NotificationType.REFERRAL_ACCEPTED)

        notifications = Notification.objects.filter(
            referral=referral, notification_type=NotificationType.REFERRAL_ACCEPTED
        )
        recipients = set(notifications.values_list("recipient_id", flat=True))
        assert recipients == {referral.referring_doctor.user_id, referral.patient.user_id}

    def test_dispatch_is_a_no_op_for_recipients_without_accounts(self, referral):
        # The factory-built patient has no linked user account by default,
        # so a reminder - which only ever targets the patient - reaches no one.
        notifications = dispatch_referral_event(referral, NotificationType.APPOINTMENT_REMINDER)
        assert notifications == []
