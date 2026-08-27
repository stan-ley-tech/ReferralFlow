from django.urls import include, path

urlpatterns = [
    path("", include("apps.users.urls")),
    path("", include("apps.hospitals.urls")),
    path("", include("apps.patients.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.referrals.urls")),
    path("", include("apps.appointments.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.integrations.urls")),
]
