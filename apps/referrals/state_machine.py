class ReferralStatus:
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ROUTED = "ROUTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

    CHOICES = [
        (DRAFT, "Draft"),
        (SUBMITTED, "Submitted"),
        (ROUTED, "Routed"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
        (SCHEDULED, "Scheduled"),
        (IN_PROGRESS, "In Progress"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
        (EXPIRED, "Expired"),
    ]

    OPEN_STATUSES = (DRAFT, SUBMITTED, ROUTED, ACCEPTED, SCHEDULED, IN_PROGRESS)
    TERMINAL_STATUSES = (COMPLETED, CANCELLED, EXPIRED, REJECTED)


# Maps each status to the set of statuses it may transition into. Anything
# not listed here - most notably out of COMPLETED, CANCELLED, and EXPIRED -
# is permanently closed to further transitions.
ALLOWED_TRANSITIONS = {
    ReferralStatus.DRAFT: {ReferralStatus.SUBMITTED, ReferralStatus.CANCELLED},
    ReferralStatus.SUBMITTED: {ReferralStatus.ROUTED, ReferralStatus.CANCELLED},
    ReferralStatus.ROUTED: {ReferralStatus.ACCEPTED, ReferralStatus.REJECTED, ReferralStatus.CANCELLED, ReferralStatus.EXPIRED},
    ReferralStatus.ACCEPTED: {ReferralStatus.SCHEDULED, ReferralStatus.CANCELLED},
    ReferralStatus.REJECTED: {ReferralStatus.ROUTED, ReferralStatus.CANCELLED},
    ReferralStatus.SCHEDULED: {ReferralStatus.IN_PROGRESS, ReferralStatus.CANCELLED},
    ReferralStatus.IN_PROGRESS: {ReferralStatus.COMPLETED, ReferralStatus.CANCELLED},
    ReferralStatus.COMPLETED: set(),
    ReferralStatus.CANCELLED: set(),
    ReferralStatus.EXPIRED: set(),
}


class InvalidStatusTransitionError(Exception):
    def __init__(self, from_status, to_status):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot transition referral from {from_status} to {to_status}.")


def assert_valid_transition(from_status, to_status):
    if to_status not in ALLOWED_TRANSITIONS.get(from_status, set()):
        raise InvalidStatusTransitionError(from_status, to_status)


def can_transition(from_status, to_status):
    return to_status in ALLOWED_TRANSITIONS.get(from_status, set())
