import pytest

from apps.referrals.state_machine import (
    InvalidStatusTransitionError,
    ReferralStatus,
    assert_valid_transition,
    can_transition,
)


class TestStateMachine:
    def test_valid_transition_does_not_raise(self):
        assert_valid_transition(ReferralStatus.DRAFT, ReferralStatus.SUBMITTED)

    def test_full_happy_path_is_valid(self):
        happy_path = [
            ReferralStatus.DRAFT,
            ReferralStatus.SUBMITTED,
            ReferralStatus.ROUTED,
            ReferralStatus.ACCEPTED,
            ReferralStatus.SCHEDULED,
            ReferralStatus.IN_PROGRESS,
            ReferralStatus.COMPLETED,
        ]
        for from_status, to_status in zip(happy_path, happy_path[1:]):
            assert_valid_transition(from_status, to_status)

    def test_completed_to_draft_is_invalid(self):
        assert not can_transition(ReferralStatus.COMPLETED, ReferralStatus.DRAFT)
        with pytest.raises(InvalidStatusTransitionError):
            assert_valid_transition(ReferralStatus.COMPLETED, ReferralStatus.DRAFT)

    @pytest.mark.parametrize("terminal_status", [ReferralStatus.COMPLETED, ReferralStatus.CANCELLED, ReferralStatus.EXPIRED])
    def test_terminal_statuses_accept_no_further_transitions(self, terminal_status):
        for candidate in dict(ReferralStatus.CHOICES):
            assert not can_transition(terminal_status, candidate)

    def test_rejected_can_be_rerouted(self):
        assert can_transition(ReferralStatus.REJECTED, ReferralStatus.ROUTED)

    def test_draft_cannot_skip_directly_to_accepted(self):
        assert not can_transition(ReferralStatus.DRAFT, ReferralStatus.ACCEPTED)
