from apps.audit.filters import AuditLogFilter
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.common.permissions import IsAdminRole
from apps.common.viewsets import BaseReadOnlyModelViewSet


class AuditLogViewSet(BaseReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("actor", "content_type").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminRole]
    filterset_class = AuditLogFilter
    ordering_fields = ["created_at"]
