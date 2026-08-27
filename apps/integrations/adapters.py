from abc import ABC, abstractmethod

import requests
from django.conf import settings


class HospitalIntegrationError(Exception):
    def __init__(self, message, *, status_code=None):
        self.status_code = status_code
        super().__init__(message)


class HospitalIntegrationAdapter(ABC):
    """
    Every external hospital system this project talks to should implement
    this interface. The service layer and Celery task only ever depend on
    this contract, so adding a second, real hospital integration later is a
    matter of writing one more adapter - not touching any calling code.
    """

    @abstractmethod
    def send_referral(self, payload: dict) -> dict:
        """Sends a referral to the external system and returns its
        acknowledgement payload. Raises HospitalIntegrationError on
        anything that should be treated as a failed attempt."""
        raise NotImplementedError


class SimulatedHospitalAdapter(HospitalIntegrationAdapter):
    """
    Stands in for a second hospital's referral intake API. It's a real HTTP
    call to an endpoint hosted by this same project (see
    `apps.integrations.views.SimulatedHospitalReceiveView`), so the request
    building, timeout handling, and error handling below exercise exactly
    the same code path a real external integration would.
    """

    def __init__(self, base_url=None, timeout=None):
        self.base_url = base_url or settings.EXTERNAL_HOSPITAL_BASE_URL
        self.timeout = timeout or settings.EXTERNAL_HOSPITAL_TIMEOUT_SECONDS

    def send_referral(self, payload: dict) -> dict:
        url = f"{self.base_url.rstrip('/')}/receive/"
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise HospitalIntegrationError(f"Network error contacting external hospital: {exc}") from exc

        if response.status_code >= 500:
            raise HospitalIntegrationError(
                f"External hospital returned server error {response.status_code}", status_code=response.status_code
            )
        if response.status_code >= 400:
            raise HospitalIntegrationError(
                f"External hospital rejected the referral: {response.text}", status_code=response.status_code
            )

        return response.json()


def get_hospital_integration_adapter() -> HospitalIntegrationAdapter:
    return SimulatedHospitalAdapter()
