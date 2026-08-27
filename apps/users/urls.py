from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import (
    MeView,
    PatientRegistrationView,
    ReferralFlowTokenObtainPairView,
    StaffUserViewSet,
)

router = DefaultRouter()
router.register("users", StaffUserViewSet, basename="staff-user")

urlpatterns = [
    path("auth/register/", PatientRegistrationView.as_view(), name="auth-register"),
    path("auth/token/", ReferralFlowTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("", include(router.urls)),
]
