from rest_framework.permissions import SAFE_METHODS, BasePermission

COORDINATION_ROLES = ("ADMIN", "REFERRAL_COORDINATOR")


class ReferralAccessPermission(BasePermission):
    """
    Role checks alone can't express "a doctor may only see referrals they
    created" or "a specialist may only see referrals assigned to them" -
    those depend on the specific referral, so this permission always
    resolves down to `has_object_permission` for anything past list/create.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(view, "action", None) == "create":
            return user.is_superuser or user.role in (*COORDINATION_ROLES, "DOCTOR")
        return True

    def has_object_permission(self, request, view, referral):
        user = request.user
        if user.is_superuser or user.role in COORDINATION_ROLES:
            return True

        if user.role == "DOCTOR":
            return referral.referring_doctor.user_id == user.id

        if user.role == "SPECIALIST":
            is_assigned = (
                referral.assigned_specialist_id is not None and referral.assigned_specialist.user_id == user.id
            ) or referral.assignments.filter(specialist__user_id=user.id).exists()
            return is_assigned

        if user.role == "NURSE":
            # Nurses have no hospital-scoped profile in this schema, so - like
            # coordinators - they support referrals network-wide, read-only.
            return request.method in SAFE_METHODS

        if user.role == "PATIENT":
            return request.method in SAFE_METHODS and referral.patient.user_id == user.id

        return False
