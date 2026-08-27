from types import SimpleNamespace

import pytest

from apps.referrals.permissions import ReferralAccessPermission
from tests.factories import DoctorFactory, PatientFactory, SpecialistFactory, UserFactory

pytestmark = pytest.mark.django_db


def _request(user, method="GET"):
    return SimpleNamespace(user=user, method=method)


class TestReferralAccessPermissionObjectLevel:
    def test_referring_doctor_has_access(self, referral):
        permission = ReferralAccessPermission()
        assert permission.has_object_permission(_request(referral.referring_doctor.user), None, referral) is True

    def test_unrelated_doctor_has_no_access(self, referral):
        other_doctor = DoctorFactory()
        permission = ReferralAccessPermission()
        assert permission.has_object_permission(_request(other_doctor.user), None, referral) is False

    def test_assigned_specialist_has_access(self, referral, specialist):
        from apps.referrals.services.referral_service import ReferralService

        referral = ReferralService.submit(referral=referral, actor=referral.referring_doctor.user)
        referral = ReferralService.route(referral=referral, specialist=specialist, actor=referral.referring_doctor.user)

        permission = ReferralAccessPermission()
        assert permission.has_object_permission(_request(specialist.user), None, referral) is True

    def test_unassigned_specialist_has_no_access(self, referral):
        other_specialist = SpecialistFactory()
        permission = ReferralAccessPermission()
        assert permission.has_object_permission(_request(other_specialist.user), None, referral) is False

    def test_owning_patient_has_read_only_access(self, referral):
        referral.patient.user = UserFactory(role="PATIENT")
        referral.patient.save(update_fields=["user"])

        permission = ReferralAccessPermission()
        assert permission.has_object_permission(_request(referral.patient.user, "GET"), None, referral) is True
        assert permission.has_object_permission(_request(referral.patient.user, "POST"), None, referral) is False

    def test_unrelated_patient_has_no_access(self, referral):
        unrelated_patient = PatientFactory()
        unrelated_patient.user = UserFactory(role="PATIENT")
        unrelated_patient.save(update_fields=["user"])

        permission = ReferralAccessPermission()
        assert permission.has_object_permission(_request(unrelated_patient.user, "GET"), None, referral) is False

    def test_admin_always_has_access(self, referral):
        admin = UserFactory(role="ADMIN", is_superuser=True)
        permission = ReferralAccessPermission()
        assert permission.has_object_permission(_request(admin), None, referral) is True
