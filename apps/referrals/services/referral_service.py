from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.referrals.exceptions import InvalidReferralTransition, SpecialistUnavailable
from apps.referrals.models import ClinicalNote, Referral, ReferralAssignment, ReferralStatusHistory
from apps.referrals.services.expiry import compute_expiry
from apps.referrals.services.reference_code import generate_reference_code
from apps.referrals.state_machine import InvalidStatusTransitionError, ReferralStatus, assert_valid_transition


def _record_transition(referral, to_status, actor, note="", **field_updates):
    """
    Applies a status change and its side-effect fields in a single save,
    appends the status history row, and writes the audit entry - the three
    things that must always happen together whenever a referral moves.
    """
    from_status = referral.status
    try:
        assert_valid_transition(from_status, to_status)
    except InvalidStatusTransitionError as exc:
        raise InvalidReferralTransition(str(exc)) from exc

    referral.status = to_status
    for field, value in field_updates.items():
        setattr(referral, field, value)
    referral.save()

    ReferralStatusHistory.objects.create(
        referral=referral,
        from_status=from_status,
        to_status=to_status,
        changed_by=actor,
        note=note,
    )
    log_action(
        action=f"referral.status_changed.{to_status.lower()}",
        target=referral,
        actor_id=actor.id if actor else None,
        metadata={"from_status": from_status, "to_status": to_status, "note": note},
    )


def _notify(referral_id, event_type):
    from apps.notifications.tasks import send_referral_notification

    transaction.on_commit(lambda: send_referral_notification.delay(referral_id, event_type))


class ReferralService:
    """
    Owns every state transition a referral can go through. Each method runs
    inside one transaction so the referral, its history entry, and its
    audit log entry either all land or none do; notification tasks are
    only queued via `transaction.on_commit` so nothing fires for a change
    that ends up rolled back.
    """

    @staticmethod
    @transaction.atomic
    def create_referral(
        *,
        patient,
        referring_doctor,
        originating_hospital,
        priority,
        reason_for_referral,
        created_by,
        clinical_summary="",
        destination_hospital=None,
        destination_department=None,
    ):
        referral = Referral.objects.create(
            reference_code=generate_reference_code(),
            patient=patient,
            referring_doctor=referring_doctor,
            originating_hospital=originating_hospital,
            destination_hospital=destination_hospital,
            destination_department=destination_department,
            priority=priority,
            reason_for_referral=reason_for_referral,
            clinical_summary=clinical_summary,
            created_by=created_by,
        )
        log_action(action="referral.created", target=referral, actor_id=created_by.id)
        return referral

    @staticmethod
    @transaction.atomic
    def submit(*, referral, actor):
        _record_transition(referral, ReferralStatus.SUBMITTED, actor, submitted_at=timezone.now())
        return referral

    @staticmethod
    @transaction.atomic
    def route(*, referral, specialist, actor, note=""):
        if not specialist.is_active or not specialist.is_accepting_referrals:
            raise SpecialistUnavailable()

        _record_transition(
            referral,
            ReferralStatus.ROUTED,
            actor,
            note=note,
            assigned_specialist=specialist,
            destination_hospital=specialist.hospital,
            destination_department=specialist.department,
            expires_at=compute_expiry(referral.priority),
            routed_at=timezone.now(),
        )
        ReferralAssignment.objects.create(referral=referral, specialist=specialist, assigned_by=actor)
        _notify(referral.id, "REFERRAL_ROUTED")
        return referral

    @staticmethod
    @transaction.atomic
    def accept(*, referral, actor, note=""):
        _resolve_pending_assignment(referral, ReferralAssignment.AssignmentStatus.ACCEPTED, note)
        _record_transition(referral, ReferralStatus.ACCEPTED, actor, note=note, accepted_at=timezone.now())
        _notify(referral.id, "REFERRAL_ACCEPTED")
        return referral

    @staticmethod
    @transaction.atomic
    def reject(*, referral, actor, reason):
        _resolve_pending_assignment(referral, ReferralAssignment.AssignmentStatus.REJECTED, reason)
        _record_transition(
            referral,
            ReferralStatus.REJECTED,
            actor,
            note=reason,
            rejected_at=timezone.now(),
            assigned_specialist=None,
        )
        _notify(referral.id, "REFERRAL_REJECTED")
        return referral

    @staticmethod
    @transaction.atomic
    def schedule(*, referral, actor, scheduled_start, scheduled_end, location, note=""):
        _record_transition(referral, ReferralStatus.SCHEDULED, actor, note=note, scheduled_at=timezone.now())

        from apps.appointments.models import Appointment

        appointment = Appointment.objects.create(
            referral=referral,
            specialist=referral.assigned_specialist,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            location=location,
            created_by=actor,
        )
        _notify(referral.id, "APPOINTMENT_SCHEDULED")
        return referral, appointment

    @staticmethod
    @transaction.atomic
    def start_consultation(*, referral, actor, note=""):
        _record_transition(referral, ReferralStatus.IN_PROGRESS, actor, note=note, started_at=timezone.now())
        return referral

    @staticmethod
    @transaction.atomic
    def complete(*, referral, actor, outcome_note):
        _record_transition(referral, ReferralStatus.COMPLETED, actor, note=outcome_note, completed_at=timezone.now())
        ClinicalNote.objects.create(
            referral=referral,
            author=actor,
            note_type=ClinicalNote.NoteType.OUTCOME,
            content=outcome_note,
        )
        _notify(referral.id, "REFERRAL_COMPLETED")
        return referral

    @staticmethod
    @transaction.atomic
    def cancel(*, referral, actor, reason=""):
        _record_transition(referral, ReferralStatus.CANCELLED, actor, note=reason, cancelled_at=timezone.now())
        _notify(referral.id, "REFERRAL_CANCELLED")
        return referral

    @staticmethod
    @transaction.atomic
    def expire(*, referral):
        _record_transition(referral, ReferralStatus.EXPIRED, actor=None, note="Automatically expired.")
        _notify(referral.id, "REFERRAL_EXPIRED")
        return referral


def _resolve_pending_assignment(referral, new_status, note):
    """Must be called before the referral's `assigned_specialist` is cleared,
    since that's how the currently pending assignment is located."""
    assignment = referral.assignments.filter(
        specialist=referral.assigned_specialist,
        status=ReferralAssignment.AssignmentStatus.PENDING,
    ).first()
    if assignment is None:
        return
    assignment.status = new_status
    assignment.decision_at = timezone.now()
    assignment.decision_note = note
    assignment.save(update_fields=["status", "decision_at", "decision_note"])
