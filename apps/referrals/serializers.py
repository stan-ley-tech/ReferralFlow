from rest_framework import serializers

from apps.hospitals.models import Specialist
from apps.referrals.models import ClinicalNote, Document, Referral, ReferralAssignment, ReferralStatusHistory


class ReferralStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source="changed_by.username", read_only=True, default=None)

    class Meta:
        model = ReferralStatusHistory
        fields = ("id", "from_status", "to_status", "changed_by", "changed_by_username", "note", "created_at")


class ReferralAssignmentSerializer(serializers.ModelSerializer):
    specialist_name = serializers.CharField(source="specialist.user.get_full_name", read_only=True)

    class Meta:
        model = ReferralAssignment
        fields = ("id", "specialist", "specialist_name", "status", "assigned_by", "decision_at", "decision_note", "created_at")


class ClinicalNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)

    class Meta:
        model = ClinicalNote
        fields = ("id", "referral", "author", "author_name", "note_type", "content", "created_at")
        read_only_fields = ("id", "referral", "author", "author_name", "created_at")


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)

    class Meta:
        model = Document
        fields = (
            "id",
            "referral",
            "uploaded_by",
            "uploaded_by_name",
            "file",
            "document_type",
            "original_filename",
            "content_type",
            "size_bytes",
            "processed",
            "created_at",
        )
        read_only_fields = (
            "id",
            "referral",
            "uploaded_by",
            "uploaded_by_name",
            "original_filename",
            "content_type",
            "size_bytes",
            "processed",
            "created_at",
        )


class ReferralListSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    referring_doctor_name = serializers.CharField(source="referring_doctor.user.get_full_name", read_only=True)
    assigned_specialist_name = serializers.CharField(
        source="assigned_specialist.user.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = Referral
        fields = (
            "id",
            "reference_code",
            "patient",
            "patient_name",
            "referring_doctor",
            "referring_doctor_name",
            "originating_hospital",
            "destination_hospital",
            "assigned_specialist",
            "assigned_specialist_name",
            "priority",
            "status",
            "expires_at",
            "created_at",
        )


class ReferralDetailSerializer(ReferralListSerializer):
    status_history = ReferralStatusHistorySerializer(many=True, read_only=True)
    assignments = ReferralAssignmentSerializer(many=True, read_only=True)
    clinical_notes = ClinicalNoteSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta(ReferralListSerializer.Meta):
        fields = ReferralListSerializer.Meta.fields + (
            "destination_department",
            "reason_for_referral",
            "clinical_summary",
            "submitted_at",
            "routed_at",
            "accepted_at",
            "rejected_at",
            "scheduled_at",
            "started_at",
            "completed_at",
            "cancelled_at",
            "created_by",
            "status_history",
            "assignments",
            "clinical_notes",
            "documents",
        )


class ReferralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = (
            "id",
            "patient",
            "referring_doctor",
            "originating_hospital",
            "destination_hospital",
            "destination_department",
            "priority",
            "reason_for_referral",
            "clinical_summary",
        )
        read_only_fields = ("id",)

    def validate_reason_for_referral(self, value):
        if not value.strip():
            raise serializers.ValidationError("A reason for referral is required.")
        return value


class RouteActionSerializer(serializers.Serializer):
    specialist = serializers.PrimaryKeyRelatedField(queryset=Specialist.objects.all())
    note = serializers.CharField(required=False, allow_blank=True, default="")


class RejectActionSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False)


class ScheduleActionSerializer(serializers.Serializer):
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    location = serializers.CharField(max_length=255)
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["scheduled_end"] <= attrs["scheduled_start"]:
            raise serializers.ValidationError("scheduled_end must be after scheduled_start.")
        return attrs


class CompleteActionSerializer(serializers.Serializer):
    outcome_note = serializers.CharField(allow_blank=False)


class CancelActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class NoteActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
