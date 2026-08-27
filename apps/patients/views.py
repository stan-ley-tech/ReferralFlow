from apps.common.viewsets import BaseModelViewSet
from apps.patients.filters import PatientFilter
from apps.patients.models import Patient
from apps.patients.permissions import HOSPITAL_SCOPED_ROLES, PatientAccessPermission, resolve_staff_hospital_id
from apps.patients.serializers import PatientSerializer


class PatientViewSet(BaseModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [PatientAccessPermission]
    filterset_class = PatientFilter
    search_fields = ["first_name", "last_name", "medical_record_number"]
    ordering_fields = ["last_name", "created_at"]

    def get_queryset(self):
        queryset = Patient.objects.select_related("registered_hospital", "user")
        user = self.request.user

        if user.is_superuser or user.role in ("ADMIN", "NURSE", "REFERRAL_COORDINATOR"):
            return queryset
        if user.role in HOSPITAL_SCOPED_ROLES:
            hospital_id = resolve_staff_hospital_id(user)
            return queryset.filter(registered_hospital_id=hospital_id) if hospital_id else queryset.none()
        if user.role == "PATIENT":
            return queryset.filter(user=user)
        return queryset.none()
