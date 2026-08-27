import logging

from apps.audit.models import AuditLog
from apps.common import request_context

logger = logging.getLogger("referralflow.audit")

_UNSET = object()


def log_action(action, target=None, actor_id=_UNSET, metadata=None):
    """
    Records an audit entry. When `actor_id` is omitted entirely, it defaults
    to the user attached to the current request context so callers deep in
    the service layer don't need to thread the request through every
    function signature. Passing `actor_id=None` explicitly - as a
    Celery-triggered system action like referral expiry does - means "no
    actor", not "look one up"; conflating the two would let a stale
    request-context value leak into audit entries for actions nothing
    authenticated actually performed.
    """
    resolved_actor_id = request_context.get_current_user_id() if actor_id is _UNSET else actor_id

    entry = AuditLog.objects.create(
        actor_id=resolved_actor_id,
        action=action,
        target=target,
        metadata=metadata or {},
        ip_address=request_context.get_client_ip(),
    )
    logger.info(
        "audit_event",
        extra={
            "action": action,
            "actor_id": resolved_actor_id,
            "target": str(target) if target else None,
        },
    )
    return entry
