import logging

from apps.audit.models import AuditLog
from apps.common import request_context

logger = logging.getLogger("referralflow.audit")


def log_action(action, target=None, actor_id=None, metadata=None):
    """
    Records an audit entry. `actor_id` defaults to the user attached to the
    current request context so callers deep in the service layer don't need
    to thread the request through every function signature.
    """
    resolved_actor_id = actor_id if actor_id is not None else request_context.get_current_user_id()

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
