"""
End-to-end coverage of the referral's primary path through the API:

    Doctor creates referral -> submits -> coordinator routes it to a
    specialist -> specialist accepts -> appointment is scheduled ->
    consultation starts -> specialist completes it -> referral is closed.

Each step is a real HTTP request through the same viewset and permission
classes production traffic uses, so this test would fail on a broken
transition, a broken permission check, or a broken serializer - not just
one of those in isolation.
"""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.notifications.models import Notification
from apps.referrals.state_machine import ReferralStatus

# transaction=True so each request's ReferralService call really commits and
# its transaction.on_commit-queued notification task actually fires, the way
# it would against a live server - the default rollback-based db fixture
# never triggers on_commit callbacks at all.
pytestmark = pytest.mark.django_db(transaction=True)


def test_full_referral_lifecycle(doctor_client, coordinator_client, specialist_client, referral, specialist):
    referral_id = referral.id

    submit_response = doctor_client.post(reverse("referral-submit", args=[referral_id]))
    assert submit_response.status_code == 200
    assert submit_response.data["status"] == ReferralStatus.SUBMITTED

    route_response = coordinator_client.post(
        reverse("referral-route", args=[referral_id]), {"specialist": specialist.id}
    )
    assert route_response.status_code == 200
    assert route_response.data["status"] == ReferralStatus.ROUTED
    assert route_response.data["assigned_specialist"] == specialist.id

    accept_response = specialist_client.post(reverse("referral-accept", args=[referral_id]))
    assert accept_response.status_code == 200
    assert accept_response.data["status"] == ReferralStatus.ACCEPTED

    start = (timezone.now() + timezone.timedelta(days=1)).isoformat()
    end = (timezone.now() + timezone.timedelta(days=1, minutes=30)).isoformat()
    schedule_response = specialist_client.post(
        reverse("referral-schedule", args=[referral_id]),
        {"scheduled_start": start, "scheduled_end": end, "location": "Clinic Room 3"},
    )
    assert schedule_response.status_code == 200
    assert schedule_response.data["status"] == ReferralStatus.SCHEDULED

    start_response = specialist_client.post(reverse("referral-start", args=[referral_id]))
    assert start_response.status_code == 200
    assert start_response.data["status"] == ReferralStatus.IN_PROGRESS

    complete_response = specialist_client.post(
        reverse("referral-complete", args=[referral_id]),
        {"outcome_note": "Consultation complete, no further action needed."},
    )
    assert complete_response.status_code == 200
    assert complete_response.data["status"] == ReferralStatus.COMPLETED

    detail_response = doctor_client.get(reverse("referral-detail", args=[referral_id]))
    assert detail_response.status_code == 200
    history_transitions = [(row["from_status"], row["to_status"]) for row in detail_response.data["status_history"]]
    assert history_transitions == [
        ("DRAFT", "SUBMITTED"),
        ("SUBMITTED", "ROUTED"),
        ("ROUTED", "ACCEPTED"),
        ("ACCEPTED", "SCHEDULED"),
        ("SCHEDULED", "IN_PROGRESS"),
        ("IN_PROGRESS", "COMPLETED"),
    ]
    assert any(note["note_type"] == "OUTCOME" for note in detail_response.data["clinical_notes"])

    notified_types = set(
        Notification.objects.filter(referral_id=referral_id).values_list("notification_type", flat=True)
    )
    assert {"REFERRAL_ROUTED", "REFERRAL_ACCEPTED", "APPOINTMENT_SCHEDULED", "REFERRAL_COMPLETED"} <= notified_types

    # A completed referral can never go back to an earlier state.
    reopen_attempt = doctor_client.post(reverse("referral-submit", args=[referral_id]))
    assert reopen_attempt.status_code == 409
