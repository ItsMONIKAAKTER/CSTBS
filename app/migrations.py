"""Targeted SQLite compatibility upgrades from CSTBS V1/V2.

Not a replacement for Alembic: back up your database before upgrading.
"""

from sqlalchemy import inspect, text

from . import db


def upgrade_v1_user_schema():
    """Add missing student roles to legacy V1 accounts, preserving records."""
    if db.engine.dialect.name != "sqlite":
        return
    inspector = inspect(db.engine)
    if not inspector.has_table("users"):
        return
    names = {column["name"] for column in inspector.get_columns("users")}
    if "role" not in names:
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL "
                "DEFAULT 'student' CHECK (role IN ('student', 'staff', 'admin'))"
            )


def upgrade_v2_booking_constraints():
    """Add the unique active-seat index to existing V2 booking tables.

    Refuse to start if bad duplicate active data exists, rather than losing or
    silently reassigning any historical booking rows.
    """
    if db.engine.dialect.name != "sqlite":
        return
    if "price_at_booking" not in {
        column["name"] for column in inspect(db.engine).get_columns("bookings")
    }:
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE bookings ADD COLUMN price_at_booking NUMERIC(10,2) "
                "NOT NULL DEFAULT 0"
            )
            # Preserve a price snapshot for legacy bookings, if any.
            connection.exec_driver_sql("""
                UPDATE bookings SET price_at_booking = COALESCE(
                    (SELECT events.price FROM seats
                     JOIN events ON events.id = seats.event_id
                     WHERE seats.id = bookings.seat_id), 0)
            """)
    with db.engine.begin() as connection:
        duplicates = connection.execute(text("""
            SELECT seat_id FROM bookings WHERE status = 'reserved'
            GROUP BY seat_id HAVING COUNT(*) > 1 LIMIT 1
        """)).first()
        if duplicates:
            raise RuntimeError(
                "Database contains conflicting active reservations. "
                "Back up and resolve duplicates before starting V3."
            )
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_booking_per_seat "
            "ON bookings (seat_id) WHERE status = 'reserved'"
        )


def upgrade_v3_seat_blocking():
    """Add non-destructive block state to existing V3 SQLite seat rows."""
    if db.engine.dialect.name != "sqlite":
        return
    if not inspect(db.engine).has_table("seats"):
        return
    names = {col["name"] for col in inspect(db.engine).get_columns("seats")}
    if "is_blocked" not in names:
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE seats ADD COLUMN is_blocked BOOLEAN NOT NULL DEFAULT 0"
            )
    # Keep booking and blocking consistent even if an admin action races with a
    # confirmation POST. SQLite evaluates these triggers inside write transactions.
    with db.engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE TRIGGER IF NOT EXISTS prevent_booking_blocked_seat_insert
            BEFORE INSERT ON bookings
            WHEN NEW.status = 'reserved' AND EXISTS (
                SELECT 1 FROM seats WHERE id = NEW.seat_id AND is_blocked = 1
            )
            BEGIN SELECT RAISE(ABORT, 'seat is blocked'); END
        """)
        connection.exec_driver_sql("""
            CREATE TRIGGER IF NOT EXISTS prevent_booking_blocked_seat_update
            BEFORE UPDATE OF status, seat_id ON bookings
            WHEN NEW.status = 'reserved' AND EXISTS (
                SELECT 1 FROM seats WHERE id = NEW.seat_id AND is_blocked = 1
            )
            BEGIN SELECT RAISE(ABORT, 'seat is blocked'); END
        """)
        connection.exec_driver_sql("""
            CREATE TRIGGER IF NOT EXISTS prevent_blocking_reserved_seat
            BEFORE UPDATE OF is_blocked ON seats
            WHEN NEW.is_blocked = 1 AND EXISTS (
                SELECT 1 FROM bookings
                WHERE seat_id = NEW.id AND status = 'reserved'
            )
            BEGIN SELECT RAISE(ABORT, 'reserved seat cannot be blocked'); END
        """)
