# CSTBS Version 2 — Database Design

## Storage and compatibility

SQLite at `instance/cstbs.db` by default; ORM via Flask-SQLAlchemy. V2 keeps the four V1 tables and extends `users` with `role`. `app/migrations.py` adds the role column non-destructively on an existing V1 SQLite database; this is **not** a general migration tool.

## Table: `users`

| Column | SQLAlchemy type | Constraints | V2 behavior |
| --- | --- | --- | --- |
| id | Integer | PK | Flask-Login identity |
| full_name | String(120) | NOT NULL | Display name |
| email | String(254) | NOT NULL, UNIQUE, indexed | Lowercase account identifier |
| password_hash | String(255) | NOT NULL | Werkzeug password hash |
| role | String(20) | NOT NULL, default `student`, CHECK allowed roles | `student`, `staff`, `admin` |
| created_at | DateTime | NOT NULL, UTC default | Account creation timestamp |

Passwords are never stored in plaintext. The signup endpoint supplies `role='student'` independently of any client field. Admin and staff assignments use the trusted local command: `flask set-role EMAIL ROLE`. Existing legacy users are assigned `student` during the V1 upgrade.

## Table: `events`

| Column | SQLAlchemy type | Constraints | V2 behavior |
| --- | --- | --- | --- |
| id | Integer | PK | Event identity |
| title | String(150) | NOT NULL | Managed by admin |
| category | String(40) | NOT NULL | Managed by admin |
| description | Text | NOT NULL | Managed by admin |
| venue | String(120) | NOT NULL | Managed by admin |
| starts_at | DateTime | NOT NULL, indexed | Naive campus-local date/time |
| price | Numeric(10,2) | NOT NULL, CHECK >= 0 | USD display price only |

Events are visible to all visitors. Administrators may create/edit/delete them. Deletion is refused when the event has seats to preserve future seat/booking references. No payment or availability workflow exists in V2.

## Retained V1 tables

**`seats`**: `id` PK; `event_id` FK to events; `section`, `row_label`, `number`; unique `(event_id, section, row_label, number)`; `number > 0`. No seat management UI.

**`bookings`**: `id` PK; `user_id` FK to users; `seat_id` FK to seats; `status` in `reserved/cancelled`; `created_at`. No booking creation or editing UI.

Relationships: `User 1:N Booking`, `Event 1:N Seat`, `Seat 1:N Booking`.

## Sample data lifecycle

The admin/local operator explicitly calls `python -m flask --app run.py seed-events` to add four illustrated events when the events table is empty. Unlike V1's startup seeding, a restart does not recreate deleted events.

## Limits and migration notes

- `db.create_all()` initializes missing tables; it does not perform arbitrary schema changes.
- Automatic V1 compatibility handles only the `users.role` column on SQLite.
- The V1 role upgrade preserves existing rows; make a backup before copying/migrating a database.
- Event time zones are not converted; configure a campus-wide timezone before production.
- SQLite foreign-key behavior and booking concurrency must be explicitly designed and tested before seat/booking features are implemented.
- Rate limiting, email verification, stronger session/deployment controls, and formal migration tooling are production hardening tasks outside V2.
