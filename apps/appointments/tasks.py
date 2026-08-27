import logging

from celery import shared_task
from django.utils import timezone

from apps.appointments.models import Appointment, AppointmentStatus

logger = logging.getLogger("referralflow.appointments")

REMINDER_WINDOW_HOURS = 24


@shared_task
def send_appointment_reminders():
    """
    Runs hourly (see config/celery.py) and picks up any scheduled
    appointment starting within the next day that hasn't been reminded yet,
    rather than scheduling a one-off task per appointment at creation time -
    that would be lost if the broker restarted before it fired.
    """
    window_end = timezone.now() + timezone.timedelta(hours=REMINDER_WINDOW_HOURS)
    due_appointments = Appointment.objects.filter(
        status=AppointmentStatus.SCHEDULED,
        reminder_sent_at__isnull=True,
        scheduled_start__lte=window_end,
        scheduled_start__gte=timezone.now(),
    )

    sent_count = 0
    for appointment in due_appointments:
        try:
            _send_single_reminder(appointment)
            sent_count += 1
        except Exception:
            logger.exception("Failed to send reminder for appointment %s", appointment.id)

    logger.info("send_appointment_reminders completed", extra={"sent_count": sent_count})
    return sent_count


def _send_single_reminder(appointment):
    from apps.notifications.tasks import send_referral_notification

    send_referral_notification.delay(appointment.referral_id, "APPOINTMENT_REMINDER")
    appointment.reminder_sent_at = timezone.now()
    appointment.save(update_fields=["reminder_sent_at"])
