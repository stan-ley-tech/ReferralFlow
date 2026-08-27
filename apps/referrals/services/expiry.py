from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.referrals.models import Priority

_EXPIRY_SETTING_BY_PRIORITY = {
    Priority.ROUTINE: "REFERRAL_DEFAULT_EXPIRY_HOURS",
    Priority.URGENT: "REFERRAL_URGENT_EXPIRY_HOURS",
    Priority.EMERGENCY: "REFERRAL_EMERGENCY_EXPIRY_HOURS",
}


def compute_expiry(priority):
    hours = getattr(settings, _EXPIRY_SETTING_BY_PRIORITY.get(priority, "REFERRAL_DEFAULT_EXPIRY_HOURS"))
    return timezone.now() + timedelta(hours=hours)
