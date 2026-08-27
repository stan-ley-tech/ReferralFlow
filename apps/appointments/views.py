from apps.appointments.filters import AppointmentFilter
from apps.appointments.models import Appointment
from apps.appointments.permissions import AppointmentAccessPermission
from apps.appointments.serializers import AppointmentSerializer
from apps.common.viewsets import BaseModelViewSet
from apps.referrals.views import referrals_visible_to


class AppointmentViewSet(BaseModelViewSet):
    """
    Appointments are created exclusively through `Referral.schedule`, which
    keeps the referral's status and its appointment in lock-step - so this
    viewset only exposes read access plus the status/notes updates a
    specialist makes as a consultation progresses.
    """

    serializer_class = AppointmentSerializer
    permission_classes = [AppointmentAccessPermission]
    filterset_class = AppointmentFilter
    ordering_fields = ["scheduled_start", "status"]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        visible_referral_ids = referrals_visible_to(self.request.user).values_list("id", flat=True)
        return (
            Appointment.objects.filter(referral_id__in=visible_referral_ids)
            .select_related("referral__patient", "specialist__user")
        )
