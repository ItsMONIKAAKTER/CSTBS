# V5.4 entrance schema extension

Existing V5.3 event/seat/booking/ticket identifiers remain stable. `app/migrations_v54.py` adds only compatible columns/tables and backfills one Gate 1 per event on legacy SQLite data.

| Table | New field | Meaning |
|---|---|---|
| `gates` | `id` PK, `event_id` FK, `name`, `is_open` | Unique name per event; closed by default |
| `seats` | `gate_id` FK to gates | Assign each physical seat to the event's entrance gate; null only for incomplete legacy inventory |
| `tickets` | `checked_in_gate_id` nullable FK to gates | Retains actual entrance used at check-in for attendance audit |

**Rules:** Gates must match their seat's event (SQLite triggers + server validation); the event `checkin_enabled` and its gate `is_open` must both be true for admission; assigned seat gate must equal scanning gate; one live ticket per attendee/event and one active seat booking remain enforced by existing unique indexes. Check-in uses conditional UPDATE, preserving single-use status under concurrent staff requests. Every legacy event is assigned Gate 1 without changing original ticket nonces or booking history. Gate assignment for a section with checked-in attendees is locked to preserve entry audit.


# CSTBS v5.3 — Database Design

## Overview

SQLite is the V5.3 source of truth. SQLAlchemy models live in `app/models.py`; the upgrade is in `app/migrations_v53.py`. One seat booking can have exactly one individual student ticket. An administrator can manage booking ownership independently of the ticket's attendee.

| Table | Key fields | Behavior |
|---|---|---|
| `users` | `id` PK, `email` unique, `student_id` unique nullable for legacy accounts, `full_name`, `password_hash`, `role`, `password_ready`, `auth_version` | Student ID required on fresh student registration. Admin activation sets `password_ready`; `auth_version` invalidates old admin sessions after reset |
| `admin_invitations` | `id`, `token_hash` unique HMAC, `target_user_id` FK, `expires_at`, `used_at`, issuer/recipient | Single-use 20-minute administrator **activation/recovery** keys; not routine login credentials |
| `events` | `id`, `title`, `category`, `description`, `venue`, `starts_at`, `price` (zero), `booking_enabled`, `checkin_enabled` | Admin controls reservation and gate status separately |
| `seats` | `id`, `event_id` FK, `section`, `row_label`, `number`, `is_blocked` | Unique `(event_id,section,row_label,number)` |
| `bookings` | `id`, `user_id` FK, `seat_id` FK, `status`, `price_at_booking`, `created_at` | Booking belongs to the **purchaser** (always free). Partial index enforces one `reserved` booking per seat. Cancelled rows retained |
| `tickets` | `id`, `booking_id` FK unique, `event_id` FK, `attendee_user_id` FK nullable, `attendee_name`, `attendee_student_id`, `nonce` unique, `status`, `checked_in_at`, `checked_in_by_id` FK | One attendee per ticket, one ticket per booking. Partial unique index `(event_id, attendee_user_id)` where status `active` or `checked_in` ensures at most one live ticket per registered student per event |

Ticket states: `active` (unspent), `checked_in` (entry consumed), `cancelled` (revoked), `unassigned` (legacy booking requires verified attendee). The `tickets.nonce` is a random, non-secret identifier signed with the persistent `TICKET_SIGNING_KEY` via itsdangerous. Signed QR payloads contain only ticket ID/nonce, never Student ID/name. Every verification checks signature, nonce, ticket state, booking state and gate status against SQLite. Separate staff-only POST consumes entry with a conditional SQL update; GET verification has no side effect.

## Integrity controls

1. `uq_active_booking_per_seat` — SQLite partial unique index on reserved bookings; prevents two active bookings for the same seat.
2. `uq_live_ticket_per_event_student` — SQLite partial unique index on live tickets; prevents one student receiving two active/checked-in tickets for the same event, including across different booking owners.
3. `trg_v53_cancel_ticket` — booking cancellation automatically invalidates linked QR ticket.
4. `trg_v53_no_ticket_on_cancelled_booking` — blocks insertion of active tickets for cancelled bookings.
5. Existing V4 seat-blocking triggers — reject booking a blocked seat and prevent blocking reserved inventory.
6. SQLite `PRAGMA foreign_keys=ON` on SQLAlchemy connections, plus bounded server validation, CSRF and role checks.

The database cannot verify consent from people named on behalf of others. Operations must obtain consent and compare institutional identity documents at entry.

## Migration of legacy V5.2 multi-seat reservations

The app **never deletes or splits** legacy booking records. Before any schema mutation of an old on-disk SQLite database, `app/backups.py` creates a private integrity-checked snapshot using the SQLite backup API. Then `app/migrations_v53.py` adds the new columns and backfills one Ticket for every existing Booking.

For an active V5.2 booking owned by a student with a registered Student ID, the first such booking for that event becomes their own `active` ticket; further bookings by the same student for that event become `unassigned` tickets, retaining their original reserved seats. Old staff/admin or ID-less owners also receive `unassigned` tickets. Cancelled bookings receive cancelled ticket history. Existing row IDs, prices, dates and status are preserved. An admin may later assign an `unassigned` ticket to a different verified registered student's ID/name through the website; duplicate active assignment is database-rejected.

Admin users are marked `password_ready = false` only on the **first** V5.3 schema upgrade; they then activate a password using a one-time key. The migration never resets passwords or ticket nonces on later runs.

## Production notes

V5.3 retains SQLite intentionally. Built-in migrations/backups are SQLite-specific; changing the database URL to PostgreSQL alone does not migrate data. Public high-volume deployment requires reviewed schema migrations, persistent volumes and keys, privacy/retention controls, verified backups and concurrency/load tests. See `docs/installation-deployment.md`.
