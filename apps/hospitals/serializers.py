from rest_framework import serializers

from apps.hospitals.models import Department, Doctor, Hospital, Specialist
from apps.users.serializers import UserSerializer


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ("id", "hospital", "name", "code", "description", "is_active")


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ("id", "name", "code", "address", "city", "phone_number", "email", "is_active")


class HospitalDetailSerializer(HospitalSerializer):
    departments = DepartmentSerializer(many=True, read_only=True)

    class Meta(HospitalSerializer.Meta):
        fields = HospitalSerializer.Meta.fields + ("departments",)


class DoctorSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Doctor
        fields = (
            "id",
            "user",
            "hospital",
            "hospital_name",
            "department",
            "department_name",
            "license_number",
            "specialization",
            "is_active",
        )


class SpecialistSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Specialist
        fields = (
            "id",
            "user",
            "hospital",
            "hospital_name",
            "department",
            "department_name",
            "specialty",
            "license_number",
            "is_accepting_referrals",
            "is_active",
        )
