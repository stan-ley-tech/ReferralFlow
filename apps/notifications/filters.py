import django_filters

from apps.notifications.models import Notification


class NotificationFilter(django_filters.FilterSet):
    class Meta:
        model = Notification
        fields = {
            "is_read": ["exact"],
            "notification_type": ["exact"],
        }
