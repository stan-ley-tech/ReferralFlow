# Workflows

## Referral lifecycle

The primary workflow this system exists for:

```
Doctor creates referral (DRAFT)
        |
        v
Doctor submits it (SUBMITTED)
        |
        v
Coordinator routes it to a specialist (ROUTED)
        |
        +-- Specialist rejects --> (REJECTED) --> coordinator re-routes
        |
        v
Specialist accepts (ACCEPTED)
        |
        v
Specialist (or coordinator) schedules an appointment (SCHEDULED)
        |
        v
Patient attends; specialist marks consultation started (IN_PROGRESS)
        |
        v
Specialist records the outcome and completes it (COMPLETED)
```

At any open state, the referring doctor or a coordinator/admin can cancel
(`CANCELLED`). A `ROUTED` referral that sits unanswered past its
`expires_at` is moved to `EXPIRED` automatically by the expiry sweep below,
not by any user action.

Every transition is recorded in `ReferralStatusHistory` with who made it,
when, and any note attached - `GET /api/v1/referrals/{id}/` returns the
full history alongside the current state, so nothing about how a referral
got to its current status is ever lost.

Priority (`ROUTINE`, `URGENT`, `EMERGENCY`) is set at creation and
determines how long a routed referral has before it expires -
`REFERRAL_EMERGENCY_EXPIRY_HOURS` and friends in settings, checked by
`apps/referrals/services/expiry.py`.

## Background jobs

| Task | Schedule | Purpose |
|---|---|---|
| `referrals.detect_expired_referrals` | every 15 minutes | Moves `ROUTED` referrals past `expires_at` to `EXPIRED`. |
| `appointments.send_appointment_reminders` | hourly | Notifies patients about appointments starting within 24 hours. |
| `referrals.generate_daily_referral_report` | daily at 06:00 | Aggregates the previous day's referral activity into a cached report. |
| `notifications.send_referral_notification` | on demand | Fires whenever a referral event happens (routed, accepted, rejected, scheduled, completed, cancelled, expired). Queued via `transaction.on_commit` so it only runs for changes that actually landed. |
| `referrals.process_uploaded_document` | on demand | Runs after a document is attached to a referral (simulates virus scan / OCR / format validation). |
| `integrations.send_referral_to_external_hospital` | on demand | Sends a referral to a partner hospital outside this system, with retry and backoff on failure. |

The schedule itself lives in `config/celery.py`. Run a worker and a beat
process to exercise all of this locally:

```bash
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info
```

(`docker-compose.yml` runs both as separate services automatically.)

## Notification routing

Not every referral event is relevant to every participant. Each event type
notifies only the people who'd actually want to know:

| Event | Notified |
|---|---|
| Referral routed | The newly assigned specialist |
| Referral accepted / completed | The referring doctor and the patient |
| Referral rejected / expired | The referring doctor |
| Referral cancelled | The referring doctor, the specialist (if assigned), and the patient |
| Appointment scheduled | The referring doctor and the patient |
| Appointment reminder | The patient |

Notifications are only created for recipients who have a linked user
account - a patient record without portal access simply doesn't receive
one, since there's nowhere to deliver it.

## External hospital integration

A referral can also be handed to a hospital that isn't part of this
system at all, via `POST /api/v1/referrals/{id}/send-external/`:

```
Coordinator sends referral externally
        |
        v
OutboundReferralRequest created (PENDING)
        |
        v
Celery task calls the adapter (SENT)
        |
        +-- Failure --> retry with exponential backoff, up to
        |               EXTERNAL_HOSPITAL_MAX_RETRIES, then FAILED
        |
        v
External system acknowledges synchronously (ACKNOWLEDGED)
        |
        v
(Later, asynchronously) external system calls our webhook with a status
update - deduplicated by event_id, so a retried delivery is a no-op
```

`apps/integrations/views.SimulatedHospitalReceiveView` stands in for the
partner hospital's intake API so this flow can be exercised end-to-end
without a second real system - see `docs/architecture.md` for how the
adapter is structured to make swapping in a real partner trivial later.
