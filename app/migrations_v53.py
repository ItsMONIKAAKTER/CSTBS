"""Non-destructive V5.2 to V5.3 SQLite upgrade.

Run after backing up instance/cstbs.db and before accepting traffic. Existing
bookings survive. Additional legacy seats for the same student become
"unassigned" tickets requiring an admin to verify an attendee; we never
silently fabricate extra admission credentials.
"""
import secrets
from sqlalchemy import inspect
from . import db


def upgrade_v53():
    if db.engine.dialect.name != "sqlite":
        # Production should run a reviewed Alembic migration before deploying.
        return
    inspector = inspect(db.engine)
    with db.engine.begin() as conn:
        ucols = {c["name"] for c in inspector.get_columns("users")}
        if "password_ready" not in ucols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN password_ready BOOLEAN NOT NULL DEFAULT 1")
            conn.exec_driver_sql("UPDATE users SET password_ready=0 WHERE role='admin'")
        if "auth_version" not in ucols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN auth_version INTEGER NOT NULL DEFAULT 0")
        ecols = {c["name"] for c in inspector.get_columns("events")}
        if "booking_enabled" not in ecols:
            conn.exec_driver_sql("ALTER TABLE events ADD COLUMN booking_enabled BOOLEAN NOT NULL DEFAULT 1")
        if "checkin_enabled" not in ecols:
            conn.exec_driver_sql("ALTER TABLE events ADD COLUMN checkin_enabled BOOLEAN NOT NULL DEFAULT 0")
        # Ensure a booking cancellation always invalidates its QR credential,
        # including cancellations executed by the older V3/V4 routes.
        conn.exec_driver_sql("""
            CREATE TRIGGER IF NOT EXISTS trg_v53_cancel_ticket
            AFTER UPDATE OF status ON bookings
            WHEN NEW.status='cancelled'
            BEGIN
              UPDATE tickets SET status='cancelled'
              WHERE booking_id=NEW.id AND status != 'cancelled';
            END
        """)
        # Protect tickets from direct SQL updates that would revive a cancelled
        # booking's ticket or assign one attendee two live tickets at an event.
        conn.exec_driver_sql("""
            CREATE TRIGGER IF NOT EXISTS trg_v53_no_ticket_on_cancelled_booking
            BEFORE INSERT ON tickets
            WHEN NEW.status IN ('active','checked_in') AND
              EXISTS (SELECT 1 FROM bookings WHERE id=NEW.booking_id AND status='cancelled')
            BEGIN SELECT RAISE(ABORT, 'cancelled booking cannot have active ticket'); END
        """)
        # Backfill only missing tickets; a rerun never changes previously issued
        # nonces, attendee assignments, check-in history or old booking prices.
        rows = conn.exec_driver_sql("""
            SELECT b.id, s.event_id, b.status, u.id, u.role, u.student_id,
                   u.full_name
            FROM bookings b JOIN seats s ON s.id=b.seat_id
              JOIN users u ON u.id=b.user_id
            WHERE NOT EXISTS (SELECT 1 FROM tickets t WHERE t.booking_id=b.id)
            ORDER BY b.created_at, b.id
        """).fetchall()
        for booking_id, event_id, booking_status, owner_id, role, sid, name in rows:
            existing = conn.exec_driver_sql("""
                SELECT 1 FROM tickets
                WHERE event_id=? AND attendee_user_id=?
                  AND status IN ('active', 'checked_in') LIMIT 1
            """, (event_id, owner_id)).first()
            valid = bool(role == 'student' and sid and not existing)
            status = 'cancelled' if booking_status == 'cancelled' else ('active' if valid else 'unassigned')
            conn.exec_driver_sql("""
                INSERT INTO tickets
                (booking_id,event_id,attendee_user_id,attendee_name,
                 attendee_student_id,nonce,status,created_at)
                VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            """, (booking_id,event_id,owner_id if valid else None,
                  name if valid else 'Legacy booking — attendee verification required',
                  sid if valid else None,secrets.token_urlsafe(24),status))
