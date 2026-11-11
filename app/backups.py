"""Consistent, private SQLite backups for schema upgrades and operator recovery."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from flask import current_app
from sqlalchemy import inspect
from . import db


def sqlite_backup(*, version_guard=False):
    """Back up an existing on-disk SQLite DB without copying a live WAL file.

    version_guard creates a snapshot before a legacy V5.1/V5.2/V5.3 schema
    changes, and skips a backup after the V5.4 gate schema is installed.
    Backup files stay below ignored instance/backups; operator stores them safely.
    """
    if db.engine.dialect.name != "sqlite":
        raise ValueError("The built-in backup command supports SQLite only.")
    filename = db.engine.url.database
    if not filename or filename == ":memory:":
        return None
    path = Path(filename)
    if not path.is_file() or not path.stat().st_size:
        return None
    if version_guard:
        inspector = inspect(db.engine)
        if not inspector.has_table("users"):
            return None
        # The V5.4 gate assignment is the current upgrade marker.
        # A V5.3 database already has password_ready but still needs backup.
        if inspector.has_table("seats") and "gate_id" in {
            c["name"] for c in inspector.get_columns("seats")
        }:
            return None
    backup_dir = Path(current_app.instance_path) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    dest = backup_dir / f"cstbs-preupgrade-{stamp}.sqlite3"
    # SQLite backup API gives a consistent snapshot even if WAL is enabled.
    with sqlite3.connect(str(path)) as source:
        with sqlite3.connect(str(dest)) as backup:
            source.backup(backup)
            result = backup.execute("PRAGMA integrity_check").fetchone()
            if result is None or result[0] != "ok":
                dest.unlink(missing_ok=True)
                raise RuntimeError("Backup integrity verification failed; migration aborted.")
    try:
        dest.chmod(0o600)
    except OSError:
        pass
    return dest
