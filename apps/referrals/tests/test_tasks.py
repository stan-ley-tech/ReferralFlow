import pytest
from django.utils import timezone

from apps.referrals.models import Referral
from apps.referrals.services.referral_service import ReferralService
from apps.referrals.state_machine import ReferralStatus
from apps.referrals.tasks import detect_expired_referrals, generate_daily_referral_report

pytestmark = pytest.mark.django_db


class TestDetectExpiredReferrals:
    def test_routed_referral_past_expiry_is_expired(self, referral, specialist):
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        referral = ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)

        Referral.objects.filter(id=referral.id).update(expires_at=timezone.now() - timezone.timedelta(hours=1))

        expired_count = detect_expired_referrals()

        referral.refresh_from_db()
        assert expired_count == 1
        assert referral.status == ReferralStatus.EXPIRED

    def test_routed_referral_not_yet_expired_is_left_alone(self, referral, specialist):
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        referral = ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)

        expired_count = detect_expired_referrals()

        referral.refresh_from_db()
        assert expired_count == 0
        assert referral.status == ReferralStatus.ROUTED

    def test_referrals_outside_routed_status_are_ignored(self, referral):
        expired_count = detect_expired_referrals()
        assert expired_count == 0


class TestGenerateDailyReferralReport:
    def test_report_counts_referrals_created_in_window(self, referral):
        report = generate_daily_referral_report()
        assert report["created_by_status"].get(ReferralStatus.DRAFT, 0) >= 1
