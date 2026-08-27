import logging
import uuid

from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action
from apps.common.permissions import IsAdminRole
from apps.integrations.models import IntegrationLog, OutboundReferralRequest, WebhookEvent
from apps.integrations.serializers import (
    IntegrationLogSerializer,
    OutboundReferralRequestSerializer,
    SimulatedReceiveSerializer,
    WebhookEventSerializer,
)

logger = logging.getLogger("referralflow.integrations")


class SimulatedHospitalReceiveView(APIView):
    """
    Stands in for a partner hospital's referral intake endpoint so the
    outbound integration path (`SimulatedHospitalAdapter`) has something
    real to call over HTTP. A production deployment would delete this view
    and point the adapter at the partner's actual API instead.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SimulatedReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data["force_failure"]:
            return Response({"error": "Simulated external system failure."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(
            {
                "status": "ACKNOWLEDGED",
                "external_reference": f"EXT-{uuid.uuid4().hex[:10].upper()}",
                "received_reference_code": serializer.validated_data["reference_code"],
            },
            status=status.HTTP_201_CREATED,
        )


class WebhookReceiveView(APIView):
    """
    Receives asynchronous status updates from the external hospital about a
    referral sent earlier. Two things make this safe against an unreliable
    network: the shared-secret header rejects unsigned callers, and the
    `event_id` uniqueness check makes replays a no-op instead of double
    processing.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        provided_secret = request.headers.get("X-Webhook-Secret")
        if provided_secret != settings.EXTERNAL_HOSPITAL_WEBHOOK_SECRET:
            return Response({"error": "Invalid webhook signature."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = WebhookEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        event, created = WebhookEvent.objects.get_or_create(
            event_id=data["event_id"],
            defaults={"source": "external_hospital", "payload": request.data},
        )
        if not created:
            logger.info("Duplicate webhook event ignored", extra={"event_id": data["event_id"]})
            return Response({"status": "duplicate_ignored"}, status=status.HTTP_200_OK)

        try:
            outbound_request = OutboundReferralRequest.objects.select_related("referral").get(
                id=data["outbound_request_id"]
            )
        except OutboundReferralRequest.DoesNotExist:
            IntegrationLog.objects.create(
                direction=IntegrationLog.Direction.INBOUND,
                level=IntegrationLog.Level.ERROR,
                message=f"Webhook referenced unknown outbound request {data['outbound_request_id']}",
                payload=request.data,
            )
            return Response({"error": "Unknown outbound_request_id."}, status=status.HTTP_404_NOT_FOUND)

        log_action(
            action="integration.webhook_received",
            target=outbound_request.referral,
            metadata={"external_status": data["status"], "note": data["note"], "event_id": data["event_id"]},
        )
        IntegrationLog.objects.create(
            direction=IntegrationLog.Direction.INBOUND,
            level=IntegrationLog.Level.INFO,
            message=f"External status update: {data['status']}",
            payload=request.data,
        )

        event.processed = True
        event.processed_at = timezone.now()
        event.save(update_fields=["processed", "processed_at"])

        return Response({"status": "processed"}, status=status.HTTP_200_OK)


class OutboundReferralRequestListView(generics.ListAPIView):
    """Administrative visibility into outbound integration attempts."""

    queryset = OutboundReferralRequest.objects.select_related("referral").all()
    serializer_class = OutboundReferralRequestSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filterset_fields = ["status", "external_hospital_code"]


class IntegrationLogListView(generics.ListAPIView):
    """Administrative visibility into integration failures and events."""

    queryset = IntegrationLog.objects.all()
    serializer_class = IntegrationLogSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filterset_fields = ["direction", "level", "integration_name"]
