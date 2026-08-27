import django_filters

from apps.appointments.models import Appointment


class AppointmentFilter(django_filters.FilterSet):
    scheduled_after = django_filters.DateTimeFilter(field_name="scheduled_start", lookup_expr="gte")
    scheduled_before = django_filters.DateTimeFilter(field_name="scheduled_start", lookup_expr="lte")

    class Meta:
        model = Appointment
        fields = {
            "status": ["exact"],
            "specialist": ["exact"],
            "referral": ["exact"],
        }
