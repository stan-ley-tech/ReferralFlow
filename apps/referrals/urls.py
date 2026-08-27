from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.referrals.views import DoctorReferralsView, HospitalReferralsView, PatientReferralsView, ReferralViewSet

router = DefaultRouter()
router.register("referrals", ReferralViewSet, basename="referral")

urlpatterns = [
    path("patients/<int:patient_id>/referrals/", PatientReferralsView.as_view(), name="patient-referrals"),
    path("doctors/<int:doctor_id>/referrals/", DoctorReferralsView.as_view(), name="doctor-referrals"),
    path("hospitals/<int:hospital_id>/referrals/", HospitalReferralsView.as_view(), name="hospital-referrals"),
    *router.urls,
]
