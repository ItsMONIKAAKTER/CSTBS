"""Non-destructive SQLite V5 → V5.1 schema and university admission update."""
from sqlalchemy import inspect
from . import db


def upgrade_v51():
    if db.engine.dialect.name != "sqlite":
        return
    inspector = inspect(db.engine)
    if inspector.has_table("users"):
        columns = {col["name"] for col in inspector.get_columns("users")}
        with db.engine.begin() as connection:
            if "student_id" not in columns:
                connection.exec_driver_sql("ALTER TABLE users ADD COLUMN student_id VARCHAR(20)")
            connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_student_id "
                "ON users (student_id) WHERE student_id IS NOT NULL")
    # Event pricing is discontinued. Historical booking price snapshots remain
    # unchanged for audit/compatibility, but no payment or revenue is reported.
    if inspector.has_table("events"):
        with db.engine.begin() as connection:
            connection.exec_driver_sql("UPDATE events SET price = 0 WHERE price <> 0")
