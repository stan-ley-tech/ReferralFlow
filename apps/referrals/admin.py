from django.contrib import admin

from apps.referrals.models import ClinicalNote, Document, Referral, ReferralAssignment, ReferralStatusHistory


class StatusHistoryInline(admin.TabularInline):
    model = ReferralStatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "note", "created_at")
    can_delete = False


class AssignmentInline(admin.TabularInline):
    model = ReferralAssignment
    extra = 0
    readonly_fields = ("specialist", "status", "assigned_by", "decision_at", "decision_note", "created_at")
    can_delete = False


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("reference_code", "patient", "status", "priority", "assigned_specialist", "created_at")
    list_filter = ("status", "priority", "originating_hospital", "destination_hospital")
    search_fields = ("reference_code", "patient__first_name", "patient__last_name")
    readonly_fields = ("reference_code", "created_at", "updated_at")
    inlines = [StatusHistoryInline, AssignmentInline]

    def get_queryset(self, request):
        return Referral.all_objects.select_related("patient", "assigned_specialist")


@admin.register(ClinicalNote)
class ClinicalNoteAdmin(admin.ModelAdmin):
    list_display = ("referral", "note_type", "author", "created_at")
    list_filter = ("note_type",)
    search_fields = ("referral__reference_code",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("referral", "document_type", "uploaded_by", "processed", "created_at")
    list_filter = ("document_type", "processed")
    search_fields = ("referral__reference_code", "original_filename")
