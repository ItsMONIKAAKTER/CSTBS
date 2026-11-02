# CSTBS Version 4 — SQLAlchemy and SQLite Design

## Entity relationships

- `User (1) → Booking (0..*)`: user owns each reservation; role `student | staff | admin`.
- `Event (1) → Seat (0..*)`: each seat belongs to a single event.
- `Seat (1) → Booking (0..*)`: one seat can have many *cancelled* historical bookings but only one *active* booking.
- Section is a **string attribute of Seat** (not a separate `Section` table). Admin section operations create/rename/remove groups of seats while retaining the same seat IDs through renames.

## Versioned tables

| Table | Core columns | V4 impact |
| --- | --- | --- |
| `users` | id, full_name, email UNIQUE, password_hash, role, created_at | Existing V2 roles; admin UI may change other users. |
| `events` | id, title, category, description, venue, starts_at, price | V2 event CRUD retained. |
| `seats` | id, event_id FK, section, row_label, number, **is_blocked** | **New V4 BOOLEAN NOT NULL DEFAULT 0**, plus existing unique `(event_id, section, row_label, number)` and positive number check. |
| `bookings` | id, user_id FK, seat_id FK, status, price_at_booking, created_at | Existing V3 records retained; admin can cancel but not delete. |

### Active reservation uniqueness (V3, retained)

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_booking_per_seat
ON bookings (seat_id) WHERE status = 'reserved';
```

### Blocked-seat integrity (new V4)

Three SQLite triggers in `app/migrations.py` reject:

1. Inserting a `reserved` booking when `seats.is_blocked = 1`.
2. Updating a booking to `reserved` (or moving a reserved booking to another seat) when its target seat is blocked.
3. Setting `seats.is_blocked = 1` while a `reserved` booking exists on that seat.

The routes also do fresh checks for understandable error messages, but the database triggers protect write races. Booking failures return a conflict message, and no partial multi-seat reservation is saved.

### V3-to-V4 SQLite upgrade

Local startup executes `db.create_all()` then explicit compatibility upgrades in this order: legacy V1 role, V2 booking price/index, **V3-to-V4 seat-blocking column and triggers**. A pre-existing V3 `seats` table gains the column through:

```sql
ALTER TABLE seats ADD COLUMN is_blocked BOOLEAN NOT NULL DEFAULT 0;
```

A fresh database already has the column through SQLAlchemy model creation. Existing rows remain present and initially unblocked. Re-running the upgrade is idempotent via column introspection and `CREATE TRIGGER IF NOT EXISTS`. Always back up your database before upgrading. These are limited **development compatibility scripts, not general production migrations**.

## Data lifecycle

1. Admin publishes an event: `Event` plus 60 default `Seat` rows.
2. Admin may add sections (`Seat.section`, `row_label`, `number`), rename sections or toggle `is_blocked` for unreserved seats.
3. User selects unblocked/unreserved seats: booking review verifies event, row membership and availability.
4. Confirmation creates one `Booking` per seat with `price_at_booking`, atomically; SQLite constraints/triggers enforce safety.
5. After commit, application sends/logs confirmation email. Failed mail does not change saved bookings.
6. Cancellation flips `Booking.status` to `cancelled`, keeps the row, frees the seat and sends/logs cancellation email. An admin may perform this for any owner.
7. Event and section removal refuse any booking record, including cancelled rows, to avoid orphaning history.

## Limitations

`Seat.section` is denormalized, sufficient for V4. Seat blocks are stored per event-seat rather than venue-wide physical locations. Changes to event or seat titles later affect how old bookings are displayed; add immutable snapshots or a normalized venue layout in a later production design. Calendar times remain campus-local naive datetime. SQLite write concurrency is appropriate for development, not a large public ticket sale.
