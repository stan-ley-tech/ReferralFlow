import random
import string

from django.utils import timezone

from apps.referrals.models import Referral

_ALPHABET = string.ascii_uppercase + string.digits


def generate_reference_code():
    """Produces a human-readable, sortable code like RF-20260827-4KQP7X.
    Collisions are astronomically unlikely but checked anyway since the
    field carries a uniqueness constraint at the database level."""
    date_part = timezone.now().strftime("%Y%m%d")
    for _ in range(5):
        suffix = "".join(random.choices(_ALPHABET, k=6))
        code = f"RF-{date_part}-{suffix}"
        if not Referral.objects.filter(reference_code=code).exists():
            return code
    raise RuntimeError("Could not generate a unique referral reference code.")
