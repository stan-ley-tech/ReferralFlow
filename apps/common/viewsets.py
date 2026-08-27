from rest_framework import generics, viewsets

from apps.common.mixins import AuditContextMixin


class BaseModelViewSet(AuditContextMixin, viewsets.ModelViewSet):
    pass


class BaseReadOnlyModelViewSet(AuditContextMixin, viewsets.ReadOnlyModelViewSet):
    pass


class BaseListAPIView(AuditContextMixin, generics.ListAPIView):
    pass


class BaseCreateAPIView(AuditContextMixin, generics.CreateAPIView):
    pass


class BaseGenericAPIView(AuditContextMixin, generics.GenericAPIView):
    pass
