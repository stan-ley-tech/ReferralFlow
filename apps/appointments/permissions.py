from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.referrals.permissions import COORDINATION_ROLES


class AppointmentAccessPermission(BasePermission):
    """Visibility mirrors the parent referral's access rules; only the
    assigned specialist or a coordinator/admin may change an appointment's
    status once it exists."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, appointment):
        user = request.user
        referral = appointment.referral

        if user.is_superuser or user.role in COORDINATION_ROLES:
            return True

        if request.method in SAFE_METHODS:
            if user.role == "DOCTOR":
                return referral.referring_doctor.user_id == user.id
            if user.role == "SPECIALIST":
                return appointment.specialist.user_id == user.id
            if user.role == "PATIENT":
                return referral.patient.user_id == user.id
            if user.role == "NURSE":
                return True
            return False

        return user.role == "SPECIALIST" and appointment.specialist.user_id == user.id
