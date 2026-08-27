from django.core.cache import cache
from rest_framework.response import Response

from apps.common.viewsets import BaseModelViewSet
from apps.hospitals.cache import HOSPITAL_LIST_CACHE_KEY, HOSPITAL_LIST_CACHE_TTL
from apps.hospitals.filters import DepartmentFilter, DoctorFilter, SpecialistFilter
from apps.hospitals.models import Department, Doctor, Hospital, Specialist
from apps.hospitals.permissions import IsAdminOrCoordinatorOrReadOnly
from apps.hospitals.serializers import (
    DepartmentSerializer,
    DoctorSerializer,
    HospitalDetailSerializer,
    HospitalSerializer,
    SpecialistSerializer,
)


class HospitalViewSet(BaseModelViewSet):
    queryset = Hospital.objects.all().prefetch_related("departments")
    permission_classes = [IsAdminOrCoordinatorOrReadOnly]
    filterset_fields = ["is_active", "city"]
    search_fields = ["name", "code", "city"]
    ordering_fields = ["name", "created_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return HospitalDetailSerializer
        return HospitalSerializer

    def list(self, request, *args, **kwargs):
        if request.query_params:
            return super().list(request, *args, **kwargs)

        cached = cache.get(HOSPITAL_LIST_CACHE_KEY)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(HOSPITAL_LIST_CACHE_KEY, response.data, timeout=HOSPITAL_LIST_CACHE_TTL)
        return response


class DepartmentViewSet(BaseModelViewSet):
    queryset = Department.objects.select_related("hospital").all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminOrCoordinatorOrReadOnly]
    filterset_class = DepartmentFilter
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]


class DoctorViewSet(BaseModelViewSet):
    queryset = Doctor.objects.select_related("user", "hospital", "department").all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAdminOrCoordinatorOrReadOnly]
    filterset_class = DoctorFilter
    search_fields = ["user__first_name", "user__last_name", "license_number"]
    ordering_fields = ["created_at"]


class SpecialistViewSet(BaseModelViewSet):
    queryset = Specialist.objects.select_related("user", "hospital", "department").all()
    serializer_class = SpecialistSerializer
    permission_classes = [IsAdminOrCoordinatorOrReadOnly]
    filterset_class = SpecialistFilter
    search_fields = ["user__first_name", "user__last_name", "specialty", "license_number"]
    ordering_fields = ["created_at"]
