from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrCoordinatorOrReadOnly(BasePermission):
    """Any authenticated user can browse hospitals, departments, and staff
    directories; only administrators and referral coordinators can change
    them, since those records drive routing decisions across the system."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return bool(user.is_superuser or user.role in ("ADMIN", "REFERRAL_COORDINATOR"))
