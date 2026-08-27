import pytest

from apps.audit.models import AuditLog
from apps.audit.services import log_action

pytestmark = pytest.mark.django_db


class TestLogAction:
    def test_log_action_records_actor_target_and_metadata(self, referral, doctor):
        entry = log_action(
            action="referral.created",
            target=referral,
            actor_id=doctor.user_id,
            metadata={"priority": referral.priority},
        )

        assert entry.pk is not None
        assert entry.actor_id == doctor.user_id
        assert entry.target == referral
        assert entry.metadata == {"priority": referral.priority}

    def test_log_action_falls_back_to_request_context_actor(self, referral, doctor):
        from apps.common import request_context

        request_context.set_current_user_id(doctor.user_id)
        try:
            entry = log_action(action="referral.viewed", target=referral)
        finally:
            request_context.set_current_user_id(None)

        assert entry.actor_id == doctor.user_id

    def test_log_action_persists_without_a_target(self):
        entry = log_action(action="system.startup")
        assert AuditLog.objects.filter(id=entry.id, content_type__isnull=True).exists()
