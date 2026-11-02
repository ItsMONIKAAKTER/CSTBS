# CSTBS Version 3 — SQLite Data Model

## Entity overview

`User 1 -> many Booking -> 1 Seat -> many-to-1 Event`.

A **Seat** is event-specific. A **Booking** refers to one seat and one user. Selecting several seats writes several bookings together; each may later be cancelled separately. There is no order-group entity in Version 3.

## Tables

### `users` (retained from V2)

| Field | Type | Constraints |
| --- | --- | --- |
| id | Integer | Primary key |
| full_name | VARCHAR(120) | NOT NULL |
| email | VARCHAR(254) | NOT NULL, UNIQUE, indexed |
| password_hash | VARCHAR(255) | NOT NULL |
| role | VARCHAR(20) | NOT NULL, default `student`, check `student`/`staff`/`admin` |
| created_at | DATETIME | NOT NULL, UTC (naive for SQLite) |

### `events` (retained from V2)

| Field | Type | Constraints |
| --- | --- | --- |
| id | Integer | Primary key |
| title | VARCHAR(150) | NOT NULL |
| category | VARCHAR(40) | NOT NULL |
| description | TEXT | NOT NULL |
| venue | VARCHAR(120) | NOT NULL |
| starts_at | DATETIME | NOT NULL, indexed; campus-local naive time |
| price | NUMERIC(10,2) | NOT NULL, check `price >= 0` |

### `seats` (fully used in V3)

| Field | Type | Constraints |
| --- | --- | --- |
| id | Integer | Primary key |
| event_id | Integer | NOT NULL, FK -> `events.id`, indexed |
| section | VARCHAR(30) | NOT NULL |
| row_label | VARCHAR(10) | NOT NULL |
| number | Integer | NOT NULL, check `number > 0` |

`UNIQUE (event_id, section, row_label, number)` prevents duplicate labels in an event/section. The default seat map creates `Main` section, rows `A`–`F`, 10 seats per row.

### `bookings` (fully used in V3)

| Field | Type | Constraints |
| --- | --- | --- |
| id | Integer | Primary key |
| user_id | Integer | NOT NULL, FK -> `users.id`, indexed |
| seat_id | Integer | NOT NULL, FK -> `seats.id`, indexed |
| status | VARCHAR(20) | NOT NULL, default `reserved`, check `reserved` / `cancelled` |
| price_at_booking | NUMERIC(10,2) | NOT NULL, saved unit price; default 0 for migration compatibility |
| created_at | DATETIME | NOT NULL, default UTC timestamp |

**Critical SQLite constraint:**

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_booking_per_seat
ON bookings (seat_id) WHERE status = 'reserved';
```

This permits a seat's **cancelled** booking records to remain as historical rows while allowing only **one active reservation**. Application-level availability checks improve UX but this index is the final concurrency safeguard.

## SQLAlchemy relations

- `User.bookings <-> Booking.user`
- `Event.seats <-> Seat.event`
- `Seat.bookings <-> Booking.seat`
- `Booking.event` convenience property resolves `booking.seat.event`.

## Reservation write transaction

1. Verify signed-in user, future event and pending session selection.
2. Query all requested `Seat` rows by `Seat.event_id`, reject duplicates/cross-event IDs/max over six.
3. Query active booked seat IDs, reject if any requested seat already taken.
4. Insert all new booking rows in one transaction, each with event-price snapshot.
5. Commit. If another transaction got the seat first, the unique index triggers `IntegrityError`; roll back **all** inserted rows and direct user to retry.

## Cancellation and event deletion

Cancel changes only `Booking.status` from `reserved` to `cancelled`, retaining the record and releasing the seat under the partial unique index. Only the booking owner can request cancellation. Admin event deletion removes unbooked seats first, then deletes the event; it refuses deletion if **any** booking (even cancelled) references a seat to preserve history.

## V2 upgrade notes

The app runs a targeted SQLite check on startup. For an older `bookings` table lacking `price_at_booking`, it adds `NUMERIC(10,2) NOT NULL DEFAULT 0`, then initializes historic prices from their corresponding event. It creates the active-seat unique index if missing. Any conflicting existing active bookings cause a startup error; **no rows are dropped or rewritten to conceal duplicates**. Events with no seats are assigned 60 default seats. Existing event seats are not overwritten.

**Always back up the database before upgrades.** `db.create_all()` is not a migration framework. The current upgrade works with the V1/V2 schema only and is intended for local development.
