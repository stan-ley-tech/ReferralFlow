import django_filters

from apps.patients.models import Patient


class PatientFilter(django_filters.FilterSet):
    class Meta:
        model = Patient
        fields = {
            "registered_hospital": ["exact"],
            "gender": ["exact"],
        }
