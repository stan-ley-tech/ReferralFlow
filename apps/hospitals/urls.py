from rest_framework.routers import DefaultRouter

from apps.hospitals.views import DepartmentViewSet, DoctorViewSet, HospitalViewSet, SpecialistViewSet

router = DefaultRouter()
router.register("hospitals", HospitalViewSet, basename="hospital")
router.register("departments", DepartmentViewSet, basename="department")
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("specialists", SpecialistViewSet, basename="specialist")

urlpatterns = router.urls
