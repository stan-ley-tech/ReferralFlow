import datetime

import factory
from factory.django import DjangoModelFactory

from apps.hospitals.models import Department, Doctor, Hospital, Specialist
from apps.patients.models import Gender, Patient
from apps.referrals.models import Priority, Referral
from apps.users.models import Role, User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = Role.DOCTOR

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "testpass123")
        if create:
            self.save()


class HospitalFactory(DjangoModelFactory):
    class Meta:
        model = Hospital

    name = factory.Sequence(lambda n: f"Test Hospital {n}")
    code = factory.Sequence(lambda n: f"TH{n:03d}")
    city = "Testville"


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department

    hospital = factory.SubFactory(HospitalFactory)
    name = "Cardiology"
    code = factory.Sequence(lambda n: f"DEPT{n:03d}")


class DoctorFactory(DjangoModelFactory):
    class Meta:
        model = Doctor

    user = factory.SubFactory(UserFactory, role=Role.DOCTOR)
    hospital = factory.SubFactory(HospitalFactory)
    department = factory.SubFactory(DepartmentFactory)
    license_number = factory.Sequence(lambda n: f"DOC-LIC-{n:05d}")


class SpecialistFactory(DjangoModelFactory):
    class Meta:
        model = Specialist

    user = factory.SubFactory(UserFactory, role=Role.SPECIALIST)
    hospital = factory.SubFactory(HospitalFactory)
    department = factory.SubFactory(DepartmentFactory)
    specialty = "Interventional Cardiology"
    license_number = factory.Sequence(lambda n: f"SPEC-LIC-{n:05d}")


class PatientFactory(DjangoModelFactory):
    class Meta:
        model = Patient

    medical_record_number = factory.Sequence(lambda n: f"MRN-{n:06d}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    date_of_birth = datetime.date(1990, 1, 1)
    gender = Gender.FEMALE
    registered_hospital = factory.SubFactory(HospitalFactory)


class ReferralFactory(DjangoModelFactory):
    class Meta:
        model = Referral

    reference_code = factory.Sequence(lambda n: f"RF-TEST-{n:06d}")
    patient = factory.SubFactory(PatientFactory)
    referring_doctor = factory.SubFactory(DoctorFactory)
    originating_hospital = factory.SelfAttribute("referring_doctor.hospital")
    priority = Priority.ROUTINE
    reason_for_referral = "Routine follow-up requested."
    created_by = factory.SelfAttribute("referring_doctor.user")
