from django.db.models import Q
from rest_framework import generics
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.common.mixins import AuditContextMixin
from apps.common.viewsets import BaseModelViewSet
from apps.referrals.exceptions import ReferralPermissionError
from apps.referrals.filters import ReferralFilter
from apps.referrals.models import Referral
from apps.referrals.permissions import COORDINATION_ROLES, ReferralAccessPermission
from apps.referrals.serializers import (
    CancelActionSerializer,
    ClinicalNoteSerializer,
    CompleteActionSerializer,
    DocumentSerializer,
    NoteActionSerializer,
    RejectActionSerializer,
    ReferralCreateSerializer,
    ReferralDetailSerializer,
    ReferralListSerializer,
    RouteActionSerializer,
    ScheduleActionSerializer,
)
from apps.referrals.services.referral_service import ReferralService

REFERRAL_SELECT_RELATED = (
    "patient",
    "referring_doctor__user",
    "originating_hospital",
    "destination_hospital",
    "destination_department",
    "assigned_specialist__user",
    "created_by",
)
REFERRAL_PREFETCH_RELATED = ("status_history", "assignments__specialist__user", "clinical_notes", "documents")


def referrals_visible_to(user, *, for_detail=False):
    """
    The single source of truth for "which referrals can this user see",
    shared by the main viewset and the per-patient/doctor/hospital list
    endpoints so the two can never drift out of sync on access rules.
    """
    queryset = Referral.objects.select_related(*REFERRAL_SELECT_RELATED)
    if for_detail:
        queryset = queryset.prefetch_related(*REFERRAL_PREFETCH_RELATED)

    if user.is_superuser or user.role in (*COORDINATION_ROLES, "NURSE"):
        return queryset
    if user.role == "DOCTOR":
        return queryset.filter(referring_doctor__user=user)
    if user.role == "SPECIALIST":
        return queryset.filter(Q(assigned_specialist__user=user) | Q(assignments__specialist__user=user)).distinct()
    if user.role == "PATIENT":
        return queryset.filter(patient__user=user)
    return queryset.none()


class ReferralViewSet(BaseModelViewSet):
    permission_classes = [ReferralAccessPermission]
    filterset_class = ReferralFilter
    search_fields = ["reference_code", "reason_for_referral", "patient__first_name", "patient__last_name"]
    ordering_fields = ["created_at", "priority", "status", "expires_at"]

    def get_queryset(self):
        return referrals_visible_to(self.request.user, for_detail=self.action == "retrieve")

    def get_serializer_class(self):
        if self.action == "create":
            return ReferralCreateSerializer
        if self.action == "list":
            return ReferralListSerializer
        return ReferralDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # ReferralCreateSerializer only exposes the input fields; the client
        # needs the generated reference_code and starting status back too.
        detail = ReferralDetailSerializer(serializer.instance)
        headers = self.get_success_headers(detail.data)
        return Response(detail.data, status=201, headers=headers)

    def perform_create(self, serializer):
        user = self.request.user
        referring_doctor = serializer.validated_data["referring_doctor"]
        if user.role == "DOCTOR" and referring_doctor.user_id != user.id:
            raise ReferralPermissionError("Doctors may only create referrals on their own behalf.")

        referral = ReferralService.create_referral(created_by=user, **serializer.validated_data)
        serializer.instance = referral

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        referral = self.get_object()
        if request.user.role == "DOCTOR" and referral.referring_doctor.user_id != request.user.id:
            raise ReferralPermissionError("Only the referring doctor may submit this referral.")
        referral = ReferralService.submit(referral=referral, actor=request.user)
        return Response(ReferralDetailSerializer(referral).data)

    @action(detail=True, methods=["post"])
    def route(self, request, pk=None):
        referral = self.get_object()
        if request.user.role not in (*COORDINATION_ROLES,) and not request.user.is_superuser:
            raise ReferralPermissionError("Only a referral coordinator or administrator may route a referral.")
        serializer = RouteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral = ReferralService.route(referral=referral, actor=request.user, **serializer.validated_data)
        return Response(ReferralDetailSerializer(referral).data)

    @action(detail=True, methods=["post"], url_path="send-external")
    def send_external(self, request, pk=None):
        """
        Hands the referral to a hospital outside this system entirely,
        rather than to one of our own specialists - the network integration
        path described in `apps.integrations`, distinct from internal
        routing above.
        """
        referral = self.get_object()
        if request.user.role not in COORDINATION_ROLES and not request.user.is_superuser:
            raise ReferralPermissionError(
                "Only a referral coordinator or administrator may send a referral externally."
            )

        external_hospital_code = request.data.get("external_hospital_code")
        if not external_hospital_code:
            raise ValidationError({"external_hospital_code": "This field is required."})

        from apps.integrations.serializers import OutboundReferralRequestSerializer
        from apps.integrations.services import initiate_outbound_referral

        outbound_request = initiate_outbound_referral(referral=referral, external_hospital_code=external_hospital_code)
        return Response(OutboundReferralRequestSerializer(outbound_request).data, status=201)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        referral = self.get_object()
        self._require_assigned_specialist(request, referral)
        serializer = NoteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral = ReferralService.accept(referral=referral, actor=request.user, **serializer.validated_data)
        return Response(ReferralDetailSerializer(referral).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        referral = self.get_object()
        self._require_assigned_specialist(request, referral)
        serializer = RejectActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral = ReferralService.reject(referral=referral, actor=request.user, **serializer.validated_data)
        return Response(ReferralDetailSerializer(referral).data)

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        referral = self.get_object()
        if request.user.role == "SPECIALIST":
            self._require_assigned_specialist(request, referral)
        elif request.user.role not in COORDINATION_ROLES and not request.user.is_superuser:
            raise ReferralPermissionError("Only the assigned specialist or a coordinator may schedule this referral.")
        serializer = ScheduleActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral, _appointment = ReferralService.schedule(
            referral=referral, actor=request.user, **serializer.validated_data
        )
        return Response(ReferralDetailSerializer(referral).data)

    @action(detail=True, methods=["post"], url_path="start", url_name="start")
    def start_consultation(self, request, pk=None):
        referral = self.get_object()
        self._require_assigned_specialist(request, referral)
        serializer = NoteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral = ReferralService.start_consultation(
            referral=referral, actor=request.user, **serializer.validated_data
        )
        return Response(ReferralDetailSerializer(referral).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        referral = self.get_object()
        self._require_assigned_specialist(request, referral)
        serializer = CompleteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral = ReferralService.complete(referral=referral, actor=request.user, **serializer.validated_data)
        return Response(ReferralDetailSerializer(referral).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        referral = self.get_object()
        user = request.user
        is_referring_doctor = user.role == "DOCTOR" and referral.referring_doctor.user_id == user.id
        if not (user.is_superuser or user.role in COORDINATION_ROLES or is_referring_doctor):
            raise ReferralPermissionError("Only the referring doctor or a coordinator may cancel this referral.")
        serializer = CancelActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral = ReferralService.cancel(referral=referral, actor=request.user, **serializer.validated_data)
        return Response(ReferralDetailSerializer(referral).data)

    @action(detail=True, methods=["get", "post"], url_path="notes")
    def notes(self, request, pk=None):
        referral = self.get_object()
        if request.method == "GET":
            serializer = ClinicalNoteSerializer(referral.clinical_notes.select_related("author"), many=True)
            return Response(serializer.data)

        serializer = ClinicalNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(referral=referral, author=request.user)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get", "post"], url_path="documents", parser_classes=[MultiPartParser, FormParser])
    def documents(self, request, pk=None):
        referral = self.get_object()
        if request.method == "GET":
            serializer = DocumentSerializer(referral.documents.select_related("uploaded_by"), many=True)
            return Response(serializer.data)

        serializer = DocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_file = serializer.validated_data["file"]
        document = serializer.save(
            referral=referral,
            uploaded_by=request.user,
            original_filename=uploaded_file.name,
            content_type=uploaded_file.content_type or "",
            size_bytes=uploaded_file.size,
        )

        from apps.referrals.tasks import process_uploaded_document

        process_uploaded_document.delay(document.id)
        return Response(DocumentSerializer(document).data, status=201)

    def _require_assigned_specialist(self, request, referral):
        user = request.user
        if user.is_superuser or user.role in COORDINATION_ROLES:
            return
        is_assigned = referral.assigned_specialist is not None and referral.assigned_specialist.user_id == user.id
        if not is_assigned:
            raise ReferralPermissionError("Only the specialist currently assigned to this referral may do that.")


class ScopedReferralListView(AuditContextMixin, generics.ListAPIView):
    """Base for the read-only /patients/{id}/referrals/, /doctors/{id}/referrals/,
    and /hospitals/{id}/referrals/ endpoints, which all reuse the main
    viewset's visibility rules, filtering, and search/ordering behaviour."""

    serializer_class = ReferralListSerializer
    permission_classes = [ReferralAccessPermission]
    filterset_class = ReferralFilter
    search_fields = ["reference_code", "reason_for_referral", "patient__first_name", "patient__last_name"]
    ordering_fields = ["created_at", "priority", "status", "expires_at"]


class PatientReferralsView(ScopedReferralListView):
    def get_queryset(self):
        return referrals_visible_to(self.request.user).filter(patient_id=self.kwargs["patient_id"])


class DoctorReferralsView(ScopedReferralListView):
    def get_queryset(self):
        return referrals_visible_to(self.request.user).filter(referring_doctor_id=self.kwargs["doctor_id"])


class HospitalReferralsView(ScopedReferralListView):
    def get_queryset(self):
        hospital_id = self.kwargs["hospital_id"]
        return referrals_visible_to(self.request.user).filter(
            Q(originating_hospital_id=hospital_id) | Q(destination_hospital_id=hospital_id)
        )
