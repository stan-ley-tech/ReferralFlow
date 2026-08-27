import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.hospitals.cache import HOSPITAL_LIST_CACHE_KEY
from tests.factories import HospitalFactory

pytestmark = pytest.mark.django_db


class TestHospitalDirectory:
    def test_list_requires_authentication(self, api_client, hospital):
        response = api_client.get(reverse("hospital-list"))
        assert response.status_code == 401

    def test_authenticated_user_can_browse_hospitals(self, doctor_client, hospital):
        response = doctor_client.get(reverse("hospital-list"))
        assert response.status_code == 200
        codes = {row["code"] for row in response.data["results"]}
        assert hospital.code in codes

    def test_doctor_cannot_create_hospital(self, doctor_client):
        response = doctor_client.post(reverse("hospital-list"), {"name": "New Hospital", "code": "NEWH"})
        assert response.status_code == 403

    def test_admin_can_create_hospital(self, admin_client):
        response = admin_client.post(reverse("hospital-list"), {"name": "New Hospital", "code": "NEWH"})
        assert response.status_code == 201


class TestHospitalListCache:
    def test_unfiltered_list_is_cached_and_invalidated_on_write(self, doctor_client, admin_client, hospital):
        cache.clear()
        first_response = doctor_client.get(reverse("hospital-list"))
        assert first_response.status_code == 200
        assert cache.get(HOSPITAL_LIST_CACHE_KEY) is not None

        HospitalFactory(name="Freshly Added Hospital", code="FRESH")
        admin_client.post(reverse("hospital-list"), {"name": "Another Hospital", "code": "ANOTH"})
        assert cache.get(HOSPITAL_LIST_CACHE_KEY) is None

        second_response = doctor_client.get(reverse("hospital-list"))
        codes = {row["code"] for row in second_response.data["results"]}
        assert "ANOTH" in codes
