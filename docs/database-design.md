# CSTBS Version 1 — Initial Database Design

## 1. Overview

Database engine: **SQLite**, managed using **SQLAlchemy / Flask-SQLAlchemy**. Default development file: `instance/cstbs.db`. Four tables are declared, but **only `events` is populated** with demo records. This is a baseline schema, not a working booking engine.

## 2. Entities

### `users`

| Column | Type | Rule | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | Primary key | Internal user ID |
| `full_name` | VARCHAR(120) | Required | Display name |
| `email` | VARCHAR(254) | Required, unique, indexed | Future login identifier |
| `password_hash` | VARCHAR(255) | Required | Placeholder for future secure authentication |
| `created_at` | DATETIME | Required, UTC default | Creation time |

**V1 behavior:** No user rows are created. Passwords are never saved by the prototype forms.

### `events`

| Column | Type | Rule | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | Primary key | Event ID |
| `title` | VARCHAR(150) | Required | Event name |
| `category` | VARCHAR(40) | Required | Event type |
| `description` | TEXT | Required | Detailed event summary |
| `venue` | VARCHAR(120) | Required | Stadium/venue |
| `starts_at` | DATETIME | Required, indexed | Event start (campus-local) |
| `price` | NUMERIC(10,2) | Required, non-negative | Illustrative entry price |

**V1 behavior:** Four records are seeded if this table is empty. All price values are demo values; no payments occur.

### `seats`

| Column | Type | Rule | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | Primary key | Seat ID |
| `event_id` | INTEGER | Foreign key → `events.id`, required | Seat's event |
| `section` | VARCHAR(30) | Required | Stadium section |
| `row_label` | VARCHAR(10) | Required | Row identifier |
| `number` | INTEGER | Required, > 0 | Seat number |

Unique constraint: `(event_id, section, row_label, number)`. No seats are seeded in V1.

### `bookings`

| Column | Type | Rule | Purpose |
| --- | --- | --- | --- |
| `id` | INTEGER | Primary key | Booking ID |
| `user_id` | INTEGER | Foreign key → `users.id`, required | Future account holder |
| `seat_id` | INTEGER | Foreign key → `seats.id`, required | Reserved seat |
| `status` | VARCHAR(20) | Required, default `reserved` | `reserved` or `cancelled` |
| `created_at` | DATETIME | Required, UTC default | Booking creation time |

No bookings are created in V1. **Booking-to-event** is derived via `Booking → Seat → Event` to avoid storing a redundant event ID.

## 3. Relationships and cardinalities

- `Event (1) → (0..N) Seat`
- `User (1) → (0..N) Booking`
- `Seat (1) → (0..N) Booking` (history may include cancelled rows)

The seat's uniqueness constraint prevents duplicate seat locations, **not** duplicate reservations. Later versions must explicitly enforce single active booking per seat and safe concurrent writes. These are not implemented here.

## 4. Integrity and limitations

- Required values use `nullable=False`; event prices and seat numbers have check constraints.
- Emails have a database-level unique constraint. Normalization, verification, and hashing workflows are **out of scope**.
- Booking status is restricted by a check constraint, but status transitions are **not** implemented.
- Booking timestamps use naive UTC in SQLite; event times are naive campus-local. A future production implementation must define and consistently apply time-zone rules.
- SQLite foreign-key enforcement should be explicitly enabled and verified before future write/booking workflows; schema declarations alone do not provide a tested reservation system.
- `db.create_all()` creates missing tables; it is **not** a schema migration system. Recreate the disposable local demo database after modifying model definitions.

## 5. Data lifecycle in V1

On application startup, the factory creates missing tables. If `events` has no rows, it inserts four example events with dates relative to the machine's current local date. Subsequent restarts preserve existing data and do not insert duplicates.

## 6. SQLAlchemy ownership

`app/models.py` defines the schema, `app/seed.py` creates optional demonstration records, `app/routes.py` queries events, and `app/__init__.py` initializes the SQLAlchemy extension and development tables.
