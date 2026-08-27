from apps.common import request_context

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    """
    Assigns a short correlation id to every request so a single referral
    action can be traced across the API log line, any Celery tasks it
    triggers, and the audit trail entry it produces.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming_id = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming_id or request_context.new_request_id()
        request_context.set_request_id(request_id)
        request.request_id = request_id

        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = request_id
        return response


class AuditContextMiddleware:
    """
    Makes the client IP available to the audit service, and resets the
    current-user context to anonymous for every request. The acting user is
    then filled back in, when there is one, by
    ``apps.common.mixins.AuditContextMixin`` - JWT authentication resolves
    inside DRF view dispatch, after Django's own middleware stack has
    already run. The reset matters because a WSGI worker thread survives
    across requests: without it, a view that skips the mixin (a plain
    ``APIView`` such as a webhook receiver) would silently see whichever
    user the *previous* request on that thread happened to authenticate as.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_context.set_client_ip(self._resolve_client_ip(request))
        request_context.set_current_user_id(None)
        return self.get_response(request)

    @staticmethod
    def _resolve_client_ip(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
