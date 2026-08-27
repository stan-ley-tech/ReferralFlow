import logging

from django.utils import timezone

from apps.notifications.models import Notification, NotificationType

logger = logging.getLogger("referralflow.notifications")

_COPY = {
    NotificationType.REFERRAL_ROUTED: "Referral {code} has been routed to you for review.",
    NotificationType.REFERRAL_ACCEPTED: "Referral {code} was accepted by the specialist.",
    NotificationType.REFERRAL_REJECTED: "Referral {code} was declined by the specialist.",
    NotificationType.REFERRAL_COMPLETED: "The consultation for referral {code} has been completed.",
    NotificationType.REFERRAL_CANCELLED: "Referral {code} has been cancelled.",
    NotificationType.REFERRAL_EXPIRED: "Referral {code} expired before a specialist responded.",
    NotificationType.APPOINTMENT_SCHEDULED: "An appointment has been scheduled for referral {code}.",
    NotificationType.APPOINTMENT_REMINDER: "Reminder: an appointment for referral {code} is coming up soon.",
}


def _recipients_for_event(referral, event_type):
    """Maps a referral lifecycle event to the users who should hear about it.
    Kept as an explicit table rather than notifying everyone attached to the
    referral, since most events are only relevant to one or two people."""
    referring_doctor_user = referral.referring_doctor.user
    patient_user = referral.patient.user
    specialist_user = referral.assigned_specialist.user if referral.assigned_specialist_id else None

    routing = {
        NotificationType.REFERRAL_ROUTED: [specialist_user],
        NotificationType.REFERRAL_ACCEPTED: [referring_doctor_user, patient_user],
        NotificationType.REFERRAL_REJECTED: [referring_doctor_user],
        NotificationType.REFERRAL_COMPLETED: [referring_doctor_user, patient_user],
        NotificationType.REFERRAL_CANCELLED: [referring_doctor_user, specialist_user, patient_user],
        NotificationType.REFERRAL_EXPIRED: [referring_doctor_user],
        NotificationType.APPOINTMENT_SCHEDULED: [referring_doctor_user, patient_user],
        NotificationType.APPOINTMENT_REMINDER: [patient_user],
    }
    return [user for user in routing.get(event_type, []) if user is not None]


def dispatch_referral_event(referral, event_type):
    """
    Creates and "sends" a notification for every relevant recipient.
    Sending is simulated by logging - swapping in a real email/SMS
    provider only means changing what happens after the Notification row
    is created, not how callers trigger it.
    """
    message = _COPY.get(event_type, "Referral {code} was updated.").format(code=referral.reference_code)
    title = event_type.replace("_", " ").title()

    created = []
    for recipient in _recipients_for_event(referral, event_type):
        notification = Notification.objects.create(
            recipient=recipient,
            referral=referral,
            notification_type=event_type,
            title=title,
            message=message,
            sent_at=timezone.now(),
        )
        logger.info(
            "notification_dispatched",
            extra={"recipient_id": recipient.id, "notification_type": event_type, "referral_id": referral.id},
        )
        created.append(notification)
    return created
