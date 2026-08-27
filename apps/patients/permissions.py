from rest_framework.permissions import SAFE_METHODS, BasePermission

STAFF_ROLES = ("ADMIN", "DOCTOR", "SPECIALIST", "NURSE", "REFERRAL_COORDINATOR")

# Nurses, coordinators, and admins aren't tied to a single hospital in this
# schema - they coordinate across the network - so only doctors and
# specialists are scoped to the hospital their profile belongs to.
HOSPITAL_SCOPED_ROLES = ("DOCTOR", "SPECIALIST")


def resolve_staff_hospital_id(user):
    profile = getattr(user, "doctor_profile", None) or getattr(user, "specialist_profile", None)
    return profile.hospital_id if profile else None


class PatientAccessPermission(BasePermission):
    """
    Staff can manage patient records; doctors and specialists are limited to
    their own hospital's patients, while nurses/coordinators/admins operate
    across the network. A patient with portal access may only read their
    own record.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.role == "PATIENT":
            return request.method in SAFE_METHODS
        return user.is_superuser or user.role in STAFF_ROLES

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or user.role not in HOSPITAL_SCOPED_ROLES:
            if user.role == "PATIENT":
                return request.method in SAFE_METHODS and obj.user_id == user.id
            return True
        hospital_id = resolve_staff_hospital_id(user)
        return hospital_id is not None and obj.registered_hospital_id == hospital_id
