from django.contrib import admin

from apps.patients.models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "medical_record_number", "registered_hospital", "gender", "is_deleted")
    list_filter = ("gender", "registered_hospital", "is_deleted")
    search_fields = ("first_name", "last_name", "medical_record_number")
    autocomplete_fields = ["user", "registered_hospital"]

    def get_queryset(self, request):
        return Patient.all_objects.select_related("registered_hospital", "user")
