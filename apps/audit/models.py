from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLog(models.Model):
    """
    Immutable record of who did what to which entity. Uses a generic
    relation so referrals, appointments, documents, and future entities can
    all be audited through one table instead of one log model per app.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100, db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor_id} at {self.created_at:%Y-%m-%d %H:%M:%S}"
