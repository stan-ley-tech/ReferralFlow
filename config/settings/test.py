from .base import *  # noqa: F401,F403

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

MEDIA_ROOT = BASE_DIR / "test_media"  # noqa: F405

LOGGING["handlers"]["console"]["level"] = "CRITICAL"  # noqa: F405
