from rest_framework import serializers

from apps.patients.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    registered_hospital_name = serializers.CharField(source="registered_hospital.name", read_only=True)

    class Meta:
        model = Patient
        fields = (
            "id",
            "user",
            "medical_record_number",
            "first_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "gender",
            "phone_number",
            "address",
            "registered_hospital",
            "registered_hospital_name",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
