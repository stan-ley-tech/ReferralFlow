from django.contrib import admin

from apps.hospitals.models import Department, Doctor, Hospital, Specialist


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "is_active")
    list_filter = ("is_active", "city")
    search_fields = ("name", "code")
    inlines = [DepartmentInline]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "hospital", "is_active")
    list_filter = ("is_active", "hospital")
    search_fields = ("name", "code")


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("user", "hospital", "department", "license_number", "is_active")
    list_filter = ("is_active", "hospital", "department")
    search_fields = ("user__first_name", "user__last_name", "license_number")
    autocomplete_fields = ["user"]


@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    list_display = ("user", "specialty", "hospital", "department", "is_accepting_referrals")
    list_filter = ("is_accepting_referrals", "is_active", "hospital", "department")
    search_fields = ("user__first_name", "user__last_name", "specialty", "license_number")
    autocomplete_fields = ["user"]
