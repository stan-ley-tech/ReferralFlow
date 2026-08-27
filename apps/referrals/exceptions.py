from rest_framework import status

from apps.common.exceptions import ApplicationError


class InvalidReferralTransition(ApplicationError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This action is not allowed for the referral's current status."
    default_code = "invalid_referral_transition"


class ReferralPermissionError(ApplicationError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You are not permitted to perform this action on this referral."
    default_code = "referral_permission_denied"


class SpecialistUnavailable(ApplicationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The selected specialist is not currently accepting referrals."
    default_code = "specialist_unavailable"
