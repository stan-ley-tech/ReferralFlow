# Architecture

## Layout

```
config/                  Django project: settings, root URLconf, Celery app
apps/
  common/                 Shared base models, middleware, pagination, exception handling
  users/                  Custom user model, roles, JWT auth
  hospitals/              Hospital, Department, Doctor, Specialist directory
  patients/                Patient records
  referrals/               Referral, state machine, service layer, clinical notes, documents
  appointments/            Appointment scheduling
  notifications/           Notification model and delivery
  audit/                   Audit log and logging service
  integrations/            Simulated external hospital integration (adapter, webhooks)
tests/                     Shared fixtures, factories, and end-to-end tests
```

Each app under `apps/` is a self-contained Django app with its own models,
serializers, views, permissions, and tests. `apps/common` holds the handful
of things every app needs (timestamped/soft-delete base models, the
paginator, the exception handler, request-scoped context) so those concerns
live in one place instead of being copy-pasted.

## Layered design

Requests flow through three layers:

1. **API layer** (`views.py`, `serializers.py`, `permissions.py`) - handles
   HTTP concerns: parsing input, checking who's allowed to do what, shaping
   the response. It has no business logic of its own.
2. **Service layer** (`referrals/services/`) - owns the referral state
   machine and every transition. All multi-step writes go through
   `ReferralService`, wrapped in `transaction.atomic()`, so a referral's
   status, its history entry, and its audit log entry are never left out of
   sync with each other.
3. **Data layer** (`models.py`) - Django ORM models with the indexes,
   constraints, and soft-delete behavior that keep the database itself
   honest, independent of whether the application code is behaving.

Views never call `Referral.objects.create()` or mutate `referral.status`
directly - they call into `ReferralService`, which is also what Celery
tasks and the Django admin would use if they needed to change a referral's
state. This is what makes "prevent invalid state transitions" enforceable
in exactly one place (`apps/referrals/state_machine.py`) rather than
scattered across every code path that might touch a referral.

## Referral state machine

```
DRAFT -> SUBMITTED -> ROUTED -> ACCEPTED -> SCHEDULED -> IN_PROGRESS -> COMPLETED
                          |          |
                          v          v
                      REJECTED   CANCELLED
                          |
                          v
                       ROUTED (re-routed to a different specialist)
```

`ROUTED` can also transition to `EXPIRED` if no specialist responds before
`expires_at` (set based on priority - see `apps/referrals/services/expiry.py`).
Every other state but `DRAFT`/`SUBMITTED`/`ROUTED`/`ACCEPTED`/`REJECTED`/
`SCHEDULED`/`IN_PROGRESS` can also move to `CANCELLED`. `COMPLETED`,
`CANCELLED`, and `EXPIRED` are terminal - `apps/referrals/state_machine.py`
has no entry for them in `ALLOWED_TRANSITIONS`, so any attempt to leave a
terminal state raises `InvalidStatusTransitionError`, which the API layer
turns into a `409 Conflict`.

## Access control

Role membership (`ADMIN`, `DOCTOR`, `SPECIALIST`, `NURSE`,
`REFERRAL_COORDINATOR`, `PATIENT`) decides what kind of thing a user can
attempt; it is checked in `permission_classes` and in `get_queryset()`
filtering. But role alone can't express "this doctor may only touch
referrals *they* created" - that requires looking at the specific object,
which is what `ReferralAccessPermission.has_object_permission()` in
`apps/referrals/permissions.py` does. Every referral viewset combines both:
a queryset scoped to what the user's role should ever see, plus an
object-level check run by DRF for detail views and custom actions. A
specialist who isn't assigned to a referral doesn't just get a 403 on it -
it's filtered out of their queryset entirely, so a 404 is returned instead,
which avoids confirming the referral even exists.

## Asynchronous work

Everything that doesn't need to block the HTTP response - notifications,
reminders, expiry sweeps, daily reporting, document processing, outbound
integration calls - runs as a Celery task against Redis. Referral state
transitions queue their follow-up tasks with `transaction.on_commit(...)`
rather than firing them immediately, so a task can never run for a database
change that ends up rolled back. `config/celery.py` defines the periodic
schedule (expiry sweep every 15 minutes, appointment reminders hourly,
daily report at 06:00).

## External integration

`apps/integrations` demonstrates the adapter pattern: `HospitalIntegrationAdapter`
is the interface the rest of the codebase depends on, and
`SimulatedHospitalAdapter` is the only implementation today. Swapping in a
real partner hospital's API later means writing a second adapter class, not
touching the service layer, the Celery task, or any view. Outbound sends
are tracked in `OutboundReferralRequest` with an attempt counter and
exponential backoff on failure; inbound webhooks are deduplicated by a
unique `event_id` on `WebhookEvent`, so a retried delivery from the
external side is a no-op rather than double-processed.

## Cross-cutting concerns

- **Structured logging**: every log line carries a request-correlation id
  (`apps/common/middleware.py`, `apps/common/logging.py`), so one referral
  action can be traced through the API log line, the Celery task it
  triggered, and the resulting audit entry.
- **Centralized exception handling**: `apps/common/exceptions.py` normalizes
  every API error - validation, permission, domain, or unexpected - into
  one response shape (`{"error": {"code", "message", "details"}}`).
- **Audit trail**: `apps/audit` records who did what to which entity through
  a generic relation, so referrals, documents, and future entities share
  one audit table instead of one per app.
- **Caching**: the hospital directory list is cached and invalidated by
  signal on write (`apps/hospitals/cache.py`), since it's read far more
  often than it changes.
