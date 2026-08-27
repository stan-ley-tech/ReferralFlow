from rest_framework import serializers

from apps.appointments.models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    referral_reference_code = serializers.CharField(source="referral.reference_code", read_only=True)
    specialist_name = serializers.CharField(source="specialist.user.get_full_name", read_only=True)
    patient_name = serializers.CharField(source="referral.patient.full_name", read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "referral",
            "referral_reference_code",
            "patient_name",
            "specialist",
            "specialist_name",
            "status",
            "scheduled_start",
            "scheduled_end",
            "location",
            "notes",
            "reminder_sent_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "referral",
            "specialist",
            "scheduled_start",
            "scheduled_end",
            "reminder_sent_at",
            "created_at",
        )
