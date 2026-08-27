from django.db import transaction

from apps.integrations.models import OutboundReferralRequest


def build_referral_payload(referral):
    return {
        "reference_code": referral.reference_code,
        "priority": referral.priority,
        "reason_for_referral": referral.reason_for_referral,
        "clinical_summary": referral.clinical_summary,
        "patient": {
            "medical_record_number": referral.patient.medical_record_number,
            "full_name": referral.patient.full_name,
            "date_of_birth": referral.patient.date_of_birth.isoformat(),
            "gender": referral.patient.gender,
        },
        "referring_hospital": referral.originating_hospital.name,
        "referring_doctor": referral.referring_doctor.user.get_full_name(),
    }


@transaction.atomic
def initiate_outbound_referral(*, referral, external_hospital_code):
    """
    Records the intent to send a referral externally before any network
    call is made, so the attempt is durable even if the process crashes
    between creating the request and the Celery task actually running.
    """
    outbound_request = OutboundReferralRequest.objects.create(
        referral=referral,
        external_hospital_code=external_hospital_code,
        payload=build_referral_payload(referral),
    )

    from apps.integrations.tasks import send_referral_to_external_hospital

    transaction.on_commit(lambda: send_referral_to_external_hospital.delay(outbound_request.id))
    return outbound_request
