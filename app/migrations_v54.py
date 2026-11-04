"""Idempotent SQLite V5.4 migration for entrance gates and entry audit.

Back up the SQLite database before running this migration. Existing ticket nonces,
bookings, students, and check-in timestamps are not altered.
"""
from sqlalchemy import inspect
from . import db


def upgrade_v54():
    if db.engine.dialect.name != "sqlite":
        return  # Other engines require a reviewed Alembic migration.
    with db.engine.begin() as conn:
        seat_columns = {c["name"] for c in inspect(conn).get_columns("seats")}
        if "gate_id" not in seat_columns:
            conn.exec_driver_sql("ALTER TABLE seats ADD COLUMN gate_id INTEGER REFERENCES gates(id)")
        ticket_columns = {c["name"] for c in inspect(conn).get_columns("tickets")}
        if "checked_in_gate_id" not in ticket_columns:
            conn.exec_driver_sql("ALTER TABLE tickets ADD COLUMN checked_in_gate_id INTEGER REFERENCES gates(id)")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_seats_gate_id ON seats(gate_id)")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_gates_event_id ON gates(event_id)")
        # Every existing event gets a first entrance, even if it has no seats yet.
        events = conn.exec_driver_sql("SELECT id FROM events ORDER BY id").fetchall()
        for (event_id,) in events:
            gate = conn.exec_driver_sql("SELECT id FROM gates WHERE event_id=? ORDER BY id LIMIT 1", (event_id,)).first()
            if gate is None:
                conn.exec_driver_sql("INSERT INTO gates(event_id,name,is_open) VALUES (?,'Gate 1',0)", (event_id,))
                gate = conn.exec_driver_sql("SELECT last_insert_rowid()").first()
            conn.exec_driver_sql("UPDATE seats SET gate_id=? WHERE event_id=? AND gate_id IS NULL", (gate[0], event_id))
        # A gate from another event must never be assigned to a seat.
        conn.exec_driver_sql("""
            CREATE TRIGGER IF NOT EXISTS trg_v54_gate_seat_insert
            BEFORE INSERT ON seats
            WHEN NEW.gate_id IS NOT NULL AND NOT EXISTS
              (SELECT 1 FROM gates WHERE id=NEW.gate_id AND event_id=NEW.event_id)
            BEGIN SELECT RAISE(ABORT,'gate must belong to seat event'); END
        """)
        conn.exec_driver_sql("""
            CREATE TRIGGER IF NOT EXISTS trg_v54_gate_seat_update
            BEFORE UPDATE OF gate_id,event_id ON seats
            WHEN NEW.gate_id IS NOT NULL AND NOT EXISTS
              (SELECT 1 FROM gates WHERE id=NEW.gate_id AND event_id=NEW.event_id)
            BEGIN SELECT RAISE(ABORT,'gate must belong to seat event'); END
        """)
