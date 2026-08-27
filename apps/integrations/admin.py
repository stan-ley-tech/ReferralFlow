from django.contrib import admin

from apps.integrations.models import IntegrationLog, OutboundReferralRequest, WebhookEvent


@admin.register(OutboundReferralRequest)
class OutboundReferralRequestAdmin(admin.ModelAdmin):
    list_display = ("referral", "external_hospital_code", "status", "attempt_count", "last_attempted_at")
    list_filter = ("status", "external_hospital_code")
    search_fields = ("referral__reference_code", "external_reference")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "source", "processed", "created_at")
    list_filter = ("source", "processed")
    search_fields = ("event_id",)


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ("integration_name", "direction", "level", "message", "created_at")
    list_filter = ("direction", "level", "integration_name")
    search_fields = ("message",)
