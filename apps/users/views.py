from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.mixins import AuditContextMixin
from apps.common.permissions import IsAdminRole
from apps.common.viewsets import BaseCreateAPIView, BaseModelViewSet
from apps.users.models import User
from apps.users.serializers import (
    PatientRegistrationSerializer,
    ReferralFlowTokenObtainPairSerializer,
    StaffUserCreateSerializer,
    UserSerializer,
)


class PatientRegistrationView(BaseCreateAPIView):
    serializer_class = PatientRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class ReferralFlowTokenObtainPairView(TokenObtainPairView):
    serializer_class = ReferralFlowTokenObtainPairSerializer


class MeView(AuditContextMixin, generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class StaffUserViewSet(BaseModelViewSet):
    """
    Administrator-only account provisioning for staff roles (doctors,
    specialists, nurses, coordinators). Patients self-register instead
    through ``PatientRegistrationView``.
    """

    queryset = User.objects.exclude(role="PATIENT").order_by("-date_joined")
    permission_classes = [IsAdminRole]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return StaffUserCreateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
