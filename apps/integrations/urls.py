from django.urls import path

from apps.integrations.views import (
    IntegrationLogListView,
    OutboundReferralRequestListView,
    SimulatedHospitalReceiveView,
    WebhookReceiveView,
)

urlpatterns = [
    path(
        "integrations/simulated-hospital/receive/",
        SimulatedHospitalReceiveView.as_view(),
        name="simulated-hospital-receive",
    ),
    path("integrations/webhooks/", WebhookReceiveView.as_view(), name="integration-webhook"),
    path(
        "integrations/outbound-requests/", OutboundReferralRequestListView.as_view(), name="outbound-referral-requests"
    ),
    path("integrations/logs/", IntegrationLogListView.as_view(), name="integration-logs"),
]
