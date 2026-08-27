# ReferralFlow

A healthcare referral management backend. It connects hospitals, doctors,
specialists, and patients through a structured referral workflow, and
tracks each referral from creation through routing, acceptance, scheduling,
consultation, and closure.

Built with Django, Django REST Framework, PostgreSQL, Celery, and Redis.

## What it does

- Models hospitals, departments, doctors, specialists, and patients as a
  connected directory rather than a flat user list.
- Runs referrals through an explicit state machine (`DRAFT` → `SUBMITTED` →
  `ROUTED` → `ACCEPTED` → `SCHEDULED` → `IN_PROGRESS` → `COMPLETED`, with
  rejection, cancellation, and expiry as side branches) and rejects any
  transition that isn't a legal move - a completed referral can never go
  back to draft.
- Enforces access with both role checks and object-level permissions: a
  doctor sees referrals they created, a specialist sees referrals assigned
  to them, a patient sees only their own record.
- Hands off notifications, appointment reminders, expiry sweeps, daily
  reporting, and document processing to Celery, so none of it blocks a
  request.
- Simulates sending a referral to a hospital outside the system entirely,
  through an adapter interface, with retries on failure and idempotent
  webhook handling for the status updates that come back.
- Keeps an audit trail of who changed what, and logs use a request
  correlation id so one action can be traced end to end.

See [`docs/architecture.md`](docs/architecture.md) for how the pieces fit
together, [`docs/workflows.md`](docs/workflows.md) for the referral
lifecycle and background jobs, and [`docs/api.md`](docs/api.md) for the
full endpoint reference.

## Stack

Python · Django · Django REST Framework · PostgreSQL · Celery · Redis ·
JWT auth (`djangorestframework-simplejwt`) · drf-spectacular (OpenAPI) ·
pytest

## Getting started

### Docker (recommended)

```bash
cp .env.example .env
docker-compose up --build
```

This brings up Postgres, Redis, the Django app, a Celery worker, and Celery
beat. The API is then available at `http://localhost:8000/api/v1/`,
interactive docs at `http://localhost:8000/api/docs/`, and the health check
at `http://localhost:8000/health/`.

Create an admin account to manage hospitals, departments, and staff
accounts through Django admin:

```bash
docker-compose exec web python manage.py createsuperuser
```

### Running locally without Docker

Requires Python 3.12+, PostgreSQL, and Redis running locally.

```bash
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -r requirements/development.txt

cp .env.example .env
# edit .env: point DATABASE_URL and REDIS_CACHE_URL/CELERY_* at your local instances

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

In separate terminals, if you want background jobs running:

```bash
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

## Configuration

All configuration is environment-based - see [`.env.example`](.env.example)
for the full list. `DJANGO_SETTINGS_MODULE` selects which settings module
loads (`config.settings.development`, `.production`, or `.test`); nothing
environment-specific is hardcoded into the settings files themselves.

## Testing

```bash
pytest
```

The suite covers models, the referral service layer and state machine,
API endpoints, permissions, authentication, Celery tasks, and an
end-to-end test that walks a referral through its full lifecycle over HTTP.
It runs against a real PostgreSQL database (`--nomigrations` for speed) and
executes Celery tasks eagerly, so nothing about async behavior is mocked
away.

```bash
flake8 apps config tests   # lint
black --check apps config tests conftest.py  # formatting
```

CI (`.github/workflows/ci.yml`) runs all of the above against Postgres and
Redis service containers on every push and pull request.

## Authentication & roles

Authentication is JWT (`POST /api/v1/auth/token/`). Six roles drive access
control: `ADMIN`, `DOCTOR`, `SPECIALIST`, `NURSE`, `REFERRAL_COORDINATOR`,
and `PATIENT`. Patients can self-register; every other role is provisioned
by an administrator through `/api/v1/users/`, since staff access to
patient data is granted deliberately rather than opened up to anyone who
signs up.

## Project layout

```
config/               Django project settings, root URLconf, Celery app
apps/
  common/               Shared base models, middleware, exception handling
  users/                Custom user model, roles, JWT auth
  hospitals/            Hospitals, departments, doctors, specialists
  patients/             Patient records
  referrals/             Referral model, state machine, service layer
  appointments/          Appointment scheduling
  notifications/         Notification delivery
  audit/                 Audit log
  integrations/          Simulated external hospital integration
tests/                  Shared fixtures, factories, end-to-end tests
docs/                   Architecture, API, and workflow documentation
```

## License

MIT - see [`LICENSE`](LICENSE).
