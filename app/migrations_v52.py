"""Non-destructive V5.1 -> V5.2 administrator login-key migration."""
from sqlalchemy import inspect
from . import db
from .models import utc_now


def upgrade_v52():
    """Add recipient binding and invalidate unbound V5.1 registration keys.

    Student accounts, events, seat bookings and registered admins are preserved.
    """
    if db.engine.dialect.name != "sqlite":
        return
    inspector = inspect(db.engine)
    if not inspector.has_table("admin_invitations"):
        return
    columns = {col["name"] for col in inspector.get_columns("admin_invitations")}
    with db.engine.begin() as connection:
        if "target_user_id" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE admin_invitations ADD COLUMN target_user_id INTEGER "
                "REFERENCES users(id)"
            )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_admin_invitations_target_user_id "
            "ON admin_invitations (target_user_id)"
        )
        # Keys issued for registration in older releases must never authenticate
        # an arbitrary email in V5.2. Only targeted login keys can be redeemed.
        connection.exec_driver_sql(
            "UPDATE admin_invitations SET used_at = ? "
            "WHERE target_user_id IS NULL AND used_at IS NULL",
            (utc_now(),)
        )
