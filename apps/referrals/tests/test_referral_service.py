import pytest
from django.utils import timezone

from apps.referrals.exceptions import InvalidReferralTransition, SpecialistUnavailable
from apps.referrals.models import ReferralAssignment
from apps.referrals.services.referral_service import ReferralService
from apps.referrals.state_machine import ReferralStatus

pytestmark = pytest.mark.django_db


class TestCreateReferral:
    def test_creates_referral_in_draft_with_generated_reference_code(self, doctor, patient):
        referral = ReferralService.create_referral(
            patient=patient,
            referring_doctor=doctor,
            originating_hospital=doctor.hospital,
            priority="ROUTINE",
            reason_for_referral="Chest pain workup",
            created_by=doctor.user,
        )
        assert referral.status == ReferralStatus.DRAFT
        assert referral.reference_code.startswith("RF-")


class TestSubmitAndRoute:
    def test_submit_moves_to_submitted_and_stamps_time(self, referral):
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        assert referral.status == ReferralStatus.SUBMITTED
        assert referral.submitted_at is not None

    def test_route_assigns_specialist_and_sets_expiry(self, referral, specialist):
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        referral = ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)

        assert referral.status == ReferralStatus.ROUTED
        assert referral.assigned_specialist_id == specialist.id
        assert referral.expires_at is not None
        assert ReferralAssignment.objects.filter(referral=referral, specialist=specialist).exists()

    def test_route_rejects_specialist_not_accepting_referrals(self, referral, specialist):
        specialist.is_accepting_referrals = False
        specialist.save(update_fields=["is_accepting_referrals"])
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)

        with pytest.raises(SpecialistUnavailable):
            ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)

    def test_cannot_route_a_draft_referral(self, referral, specialist):
        with pytest.raises(InvalidReferralTransition):
            ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)


class TestAcceptRejectReroute:
    def _routed_referral(self, referral, specialist):
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        return ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)

    def test_accept_marks_assignment_accepted(self, referral, specialist):
        referral = self._routed_referral(referral, specialist)
        referral = ReferralService.accept(referral=referral, actor=specialist.user)

        assert referral.status == ReferralStatus.ACCEPTED
        assignment = referral.assignments.get(specialist=specialist)
        assert assignment.status == ReferralAssignment.AssignmentStatus.ACCEPTED

    def test_reject_clears_specialist_and_allows_reroute(self, referral, specialist):
        referral = self._routed_referral(referral, specialist)
        referral = ReferralService.reject(referral=referral, actor=specialist.user, reason="Not my specialty")

        assert referral.status == ReferralStatus.REJECTED
        assert referral.assigned_specialist_id is None
        rejected_assignment = referral.assignments.get(specialist=specialist)
        assert rejected_assignment.status == ReferralAssignment.AssignmentStatus.REJECTED

        # Coordinator reroutes to a different specialist after rejection.
        from tests.factories import SpecialistFactory

        second_specialist = SpecialistFactory(hospital=specialist.hospital, department=specialist.department)
        referral = ReferralService.route(
            referral=referral, specialist=second_specialist, actor=referral.referring_doctor.user
        )
        assert referral.status == ReferralStatus.ROUTED
        assert referral.assigned_specialist_id == second_specialist.id


class TestScheduleAndComplete:
    def _accepted_referral(self, referral, specialist):
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        referral = ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)
        return ReferralService.accept(referral=referral, actor=specialist.user)

    def test_schedule_creates_appointment(self, referral, specialist):
        referral = self._accepted_referral(referral, specialist)
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(minutes=30)

        referral, appointment = ReferralService.schedule(
            referral=referral, actor=specialist.user, scheduled_start=start, scheduled_end=end, location="Room 1"
        )
        assert referral.status == ReferralStatus.SCHEDULED
        assert appointment.referral_id == referral.id
        assert appointment.specialist_id == specialist.id

    def test_complete_requires_in_progress_and_creates_outcome_note(self, referral, specialist):
        referral = self._accepted_referral(referral, specialist)
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(minutes=30)
        referral, _ = ReferralService.schedule(
            referral=referral, actor=specialist.user, scheduled_start=start, scheduled_end=end, location="Room 1"
        )

        with pytest.raises(InvalidReferralTransition):
            ReferralService.complete(referral=referral, actor=specialist.user, outcome_note="too early")

        referral = ReferralService.start_consultation(referral=referral, actor=specialist.user)
        referral = ReferralService.complete(referral=referral, actor=specialist.user, outcome_note="Stable, discharge.")

        assert referral.status == ReferralStatus.COMPLETED
        assert referral.clinical_notes.filter(note_type="OUTCOME", content="Stable, discharge.").exists()


class TestStatusHistoryAndAudit:
    def test_every_transition_is_recorded_in_status_history(self, referral, specialist):
        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        referral = ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)
        referral = ReferralService.accept(referral=referral, actor=specialist.user)

        transitions = list(referral.status_history.values_list("from_status", "to_status"))
        assert transitions == [
            ("DRAFT", "SUBMITTED"),
            ("SUBMITTED", "ROUTED"),
            ("ROUTED", "ACCEPTED"),
        ]
