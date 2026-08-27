from apps.common import request_context


class AuditContextMixin:
    """
    Records the authenticated user against the current request context as
    soon as DRF has resolved authentication, so the audit service can
    attribute actions correctly regardless of which auth class ran.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        user = getattr(request, "user", None)
        request_context.set_current_user_id(user.id if user and user.is_authenticated else None)
