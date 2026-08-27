from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.viewsets import BaseModelViewSet
from apps.notifications.filters import NotificationFilter
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationViewSet(BaseModelViewSet):
    """Every user only ever sees their own notifications - there is no
    cross-user visibility rule to express here, unlike referrals."""

    serializer_class = NotificationSerializer
    filterset_class = NotificationFilter
    ordering_fields = ["created_at"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related("referral")

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"marked_read": updated})
