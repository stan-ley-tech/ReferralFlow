from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True

# Uses the always-eager broker unless a real Redis instance is configured,
# so `manage.py runserver` works without Docker for quick iteration.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)  # noqa: F405
CELERY_TASK_EAGER_PROPAGATES = True
