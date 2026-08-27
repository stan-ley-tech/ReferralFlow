import django_filters

from apps.hospitals.models import Department, Doctor, Specialist


class DepartmentFilter(django_filters.FilterSet):
    class Meta:
        model = Department
        fields = {
            "hospital": ["exact"],
            "is_active": ["exact"],
        }


class DoctorFilter(django_filters.FilterSet):
    class Meta:
        model = Doctor
        fields = {
            "hospital": ["exact"],
            "department": ["exact"],
            "is_active": ["exact"],
        }


class SpecialistFilter(django_filters.FilterSet):
    class Meta:
        model = Specialist
        fields = {
            "hospital": ["exact"],
            "department": ["exact"],
            "specialty": ["exact", "icontains"],
            "is_accepting_referrals": ["exact"],
            "is_active": ["exact"],
        }
