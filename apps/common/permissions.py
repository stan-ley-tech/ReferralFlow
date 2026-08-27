from rest_framework.permissions import BasePermission


def has_any_role(*roles):
    """
    Returns a DRF permission class restricting access to the given roles.
    Kept as a factory rather than one generic class with a `roles` attribute
    so it can be used directly in `permission_classes` tuples.
    """

    class _HasAnyRole(BasePermission):
        message = f"This action requires one of the following roles: {', '.join(roles)}."

        def has_permission(self, request, view):
            user = request.user
            return bool(user and user.is_authenticated and (user.is_superuser or user.role in roles))

    return _HasAnyRole


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.role == "ADMIN"))
