from django.contrib import admin

from apps.appointments.models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("referral", "specialist", "status", "scheduled_start", "scheduled_end")
    list_filter = ("status",)
    search_fields = ("referral__reference_code",)
    autocomplete_fields = ["specialist"]
