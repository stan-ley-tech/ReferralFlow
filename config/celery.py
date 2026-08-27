import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("referralflow")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "detect-expired-referrals": {
        "task": "apps.referrals.tasks.detect_expired_referrals",
        "schedule": crontab(minute="*/15"),
    },
    "send-appointment-reminders": {
        "task": "apps.appointments.tasks.send_appointment_reminders",
        "schedule": crontab(minute=0),
    },
    "generate-daily-referral-report": {
        "task": "apps.referrals.tasks.generate_daily_referral_report",
        "schedule": crontab(hour=6, minute=0),
    },
}
