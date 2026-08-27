import pytest

from apps.users.models import Role
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestUserRoleProperties:
    @pytest.mark.parametrize(
        "role, property_name",
        [
            (Role.ADMIN, "is_admin"),
            (Role.DOCTOR, "is_doctor"),
            (Role.SPECIALIST, "is_specialist"),
            (Role.NURSE, "is_nurse"),
            (Role.REFERRAL_COORDINATOR, "is_referral_coordinator"),
            (Role.PATIENT, "is_patient_user"),
        ],
    )
    def test_role_property_is_true_only_for_matching_role(self, role, property_name):
        user = UserFactory(role=role)
        assert getattr(user, property_name) is True

        other_role = Role.ADMIN if role != Role.ADMIN else Role.DOCTOR
        other_user = UserFactory(role=other_role)
        assert getattr(other_user, property_name) is False

    def test_str_includes_role(self):
        user = UserFactory(role=Role.SPECIALIST, first_name="Ada", last_name="Lovelace")
        assert "SPECIALIST" in str(user)
