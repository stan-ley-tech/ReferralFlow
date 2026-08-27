from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "channel", "is_read", "created_at")
    list_filter = ("notification_type", "channel", "is_read")
    search_fields = ("recipient__username", "title")
