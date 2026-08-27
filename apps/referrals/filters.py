import django_filters

from apps.referrals.models import Referral


class ReferralFilter(django_filters.FilterSet):
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Referral
        fields = {
            "status": ["exact"],
            "priority": ["exact"],
            "originating_hospital": ["exact"],
            "destination_hospital": ["exact"],
            "destination_department": ["exact"],
            "assigned_specialist": ["exact"],
        }
