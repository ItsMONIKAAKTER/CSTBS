"""Minimal, non-destructive SQLite upgrade from the V1 user schema.

This is an intentionally narrow compatibility step, not a generic migration tool.
It does not modify event, seat, or booking rows.
"""

from sqlalchemy import inspect

from . import db


def upgrade_v1_user_schema():
    """Add role='student' to legacy V1 users without losing existing rows."""
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
