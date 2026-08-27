import pytest
from django.urls import reverse

from apps.users.models import Role, User

pytestmark = pytest.mark.django_db


class TestPatientRegistration:
    def test_public_registration_creates_a_patient_role_account(self, api_client):
        response = api_client.post(
            reverse("auth-register"),
            {
                "username": "newpatient",
                "email": "p@example.com",
                "password": "S3cure!Pass",
                "first_name": "A",
                "last_name": "B",
            },
        )
        assert response.status_code == 201, response.data
        user = User.objects.get(username="newpatient")
        assert user.role == Role.PATIENT

    def test_registration_rejects_weak_password(self, api_client):
        response = api_client.post(
            reverse("auth-register"),
            {"username": "weakpw", "email": "w@example.com", "password": "123"},
        )
        assert response.status_code == 400


class TestTokenAuth:
    def test_obtain_token_with_valid_credentials(self, api_client, doctor):
        response = api_client.post(
            reverse("token-obtain-pair"), {"username": doctor.user.username, "password": "testpass123"}
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert response.data["user"]["role"] == Role.DOCTOR

    def test_obtain_token_with_invalid_credentials_fails(self, api_client, doctor):
        response = api_client.post(
            reverse("token-obtain-pair"), {"username": doctor.user.username, "password": "wrong"}
        )
        assert response.status_code == 401

    def test_protected_endpoint_requires_authentication(self, api_client):
        response = api_client.get(reverse("auth-me"))
        assert response.status_code == 401

    def test_me_endpoint_returns_current_user(self, doctor_client, doctor):
        response = doctor_client.get(reverse("auth-me"))
        assert response.status_code == 200
        assert response.data["username"] == doctor.user.username


class TestStaffProvisioning:
    def test_only_admin_can_create_staff_accounts(self, admin_client):
        response = admin_client.post(
            reverse("staff-user-list"),
            {"username": "newnurse", "email": "n@example.com", "password": "S3cure!Pass", "role": Role.NURSE},
        )
        assert response.status_code == 201, response.data

    def test_non_admin_cannot_create_staff_accounts(self, doctor_client):
        response = doctor_client.post(
            reverse("staff-user-list"),
            {"username": "newnurse2", "email": "n2@example.com", "password": "S3cure!Pass", "role": Role.NURSE},
        )
        assert response.status_code == 403
