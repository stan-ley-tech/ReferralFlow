# API Reference

Base URL: `/api/v1/`. Interactive documentation is served at `/api/docs/`
(Swagger UI) and the raw OpenAPI schema at `/api/schema/`, both generated
from the code by drf-spectacular rather than maintained by hand.

## Authentication

JWT, via `djangorestframework-simplejwt`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register/` | Public self-registration. Always creates a `PATIENT` account. |
| POST | `/api/v1/auth/token/` | Obtain an access/refresh token pair. |
| POST | `/api/v1/auth/token/refresh/` | Exchange a refresh token for a new access token. |
| GET/PATCH | `/api/v1/auth/me/` | Retrieve or update the current user's profile. |
| GET/POST/PATCH/DELETE | `/api/v1/users/` | Admin-only provisioning of staff accounts (doctor, specialist, nurse, coordinator, admin). |

Send the access token as `Authorization: Bearer <token>`. Staff accounts
(everything except `PATIENT`) are provisioned by an administrator through
`/api/v1/users/` rather than self-registered - hospital system access is
deliberately granted, not opened up.

## Directory

| Method | Path | Description |
|---|---|---|
| GET/POST/PATCH/DELETE | `/api/v1/hospitals/` | Hospitals. Read: any authenticated user. Write: admin/coordinator. |
| GET/POST/PATCH/DELETE | `/api/v1/departments/` | Departments within a hospital. |
| GET/POST/PATCH/DELETE | `/api/v1/doctors/` | Doctor directory. |
| GET/POST/PATCH/DELETE | `/api/v1/specialists/` | Specialist directory, including `is_accepting_referrals`. |
| GET/POST/PATCH/DELETE | `/api/v1/patients/` | Patient records, hospital-scoped for doctors/specialists. |

## Referrals

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/referrals/` | Create a referral (`DRAFT`). |
| GET | `/api/v1/referrals/` | List referrals visible to the current user. |
| GET | `/api/v1/referrals/{id}/` | Referral detail, including status history, assignments, notes, documents. |
| POST | `/api/v1/referrals/{id}/submit/` | `DRAFT` -> `SUBMITTED`. Referring doctor only. |
| POST | `/api/v1/referrals/{id}/route/` | `SUBMITTED`/`REJECTED` -> `ROUTED`. Assigns a specialist. Coordinator/admin only. Body: `{"specialist": <id>, "note": ""}` |
| POST | `/api/v1/referrals/{id}/accept/` | `ROUTED` -> `ACCEPTED`. Assigned specialist only. |
| POST | `/api/v1/referrals/{id}/reject/` | `ROUTED` -> `REJECTED`. Assigned specialist only. Body: `{"reason": "..."}` |
| POST | `/api/v1/referrals/{id}/schedule/` | `ACCEPTED` -> `SCHEDULED`. Creates an appointment. Body: `{"scheduled_start", "scheduled_end", "location"}` |
| POST | `/api/v1/referrals/{id}/start/` | `SCHEDULED` -> `IN_PROGRESS`. |
| POST | `/api/v1/referrals/{id}/complete/` | `IN_PROGRESS` -> `COMPLETED`. Body: `{"outcome_note": "..."}` |
| POST | `/api/v1/referrals/{id}/cancel/` | Any open status -> `CANCELLED`. Referring doctor or coordinator/admin. |
| POST | `/api/v1/referrals/{id}/send-external/` | Hands the referral to a hospital outside this system. Body: `{"external_hospital_code": "..."}` |
| GET/POST | `/api/v1/referrals/{id}/notes/` | Clinical notes on the referral. |
| GET/POST | `/api/v1/referrals/{id}/documents/` | Attached documents (multipart upload). |
| GET | `/api/v1/patients/{patient_id}/referrals/` | Referrals for one patient. |
| GET | `/api/v1/doctors/{doctor_id}/referrals/` | Referrals created by one doctor. |
| GET | `/api/v1/hospitals/{hospital_id}/referrals/` | Referrals originating from or destined for one hospital. |

Invalid transitions (e.g. `COMPLETED` -> anything) return `409 Conflict`.
Acting outside your role or relationship to the referral returns `403`
(or `404` if the object is filtered out of your visible queryset entirely).

## Appointments & Notifications

| Method | Path | Description |
|---|---|---|
| GET/PATCH | `/api/v1/appointments/` | Read-only except for status/notes updates; created only via `referrals/{id}/schedule/`. |
| GET | `/api/v1/notifications/` | The current user's own notifications. |
| POST | `/api/v1/notifications/{id}/mark-read/` | Mark one notification read. |
| POST | `/api/v1/notifications/mark-all-read/` | Mark all of the current user's notifications read. |

## Integrations

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/integrations/simulated-hospital/receive/` | Stands in for a partner hospital's intake API. |
| POST | `/api/v1/integrations/webhooks/` | Receives async status updates from the external hospital. Requires `X-Webhook-Secret`. |
| GET | `/api/v1/integrations/outbound-requests/` | Admin visibility into outbound send attempts. |
| GET | `/api/v1/integrations/logs/` | Admin visibility into integration successes/failures. |

## Audit

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/audit-logs/` | Admin-only, read-only audit trail. |

## Filtering, search, ordering, pagination

List endpoints accept:

- `?search=` - free-text search over the fields configured per endpoint (e.g. reference code, patient name).
- Field filters, e.g. `?status=ROUTED&priority=URGENT` on `/referrals/`.
- `?ordering=created_at` or `?ordering=-created_at` for sorting.
- `?page=` and `?page_size=` for pagination.

Paginated responses look like:

```json
{
  "count": 42,
  "total_pages": 3,
  "current_page": 1,
  "next": "http://.../api/v1/referrals/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

## Error format

Every error response - validation, permission, not-found, domain, or
unexpected - has the same shape:

```json
{
  "error": {
    "code": "invalid_referral_transition",
    "message": "This action is not allowed for the referral's current status.",
    "details": {"detail": "Cannot transition referral from COMPLETED to CANCELLED."}
  }
}
```

## Health check

`GET /health/` - checks the database and cache are reachable, not just that
the process is running. Returns `200` with `{"status": "ok", ...}` when
healthy, `503` with `{"status": "degraded", ...}` otherwise. No
authentication required, so it's safe for load balancers and uptime
monitors to poll.
