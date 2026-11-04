"""One-time administrator invitations: unguessable, hashed, expiring, atomic.

Never store raw keys, put them in URLs, or place them in Flask session cookies.
Local bootstrap creation is purposely disabled for TESTING/production startup.
"""

from datetime import timedelta
import hashlib
import hmac
import secrets

from flask import current_app
from sqlalchemy import func, select, update

from . import db
from .models import AdminInvitation, User, utc_now


def _fingerprint(key):
    secret = current_app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(secret, key.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def issue_key(*, bootstrap=False, created_by=None, minutes=60):
    """Persist a hash; return raw key only to the caller once."""
    key = "CSTBS-" + secrets.token_urlsafe(24)
    row = AdminInvitation(token_hash=_fingerprint(key), bootstrap=bootstrap,
        created_by_id=created_by, expires_at=utc_now() + timedelta(minutes=minutes))
    db.session.add(row)
    db.session.commit()
    return key


def active_bootstrap_exists():
    return db.session.scalar(select(AdminInvitation.id).where(
        AdminInvitation.bootstrap.is_(True),
        AdminInvitation.used_at.is_(None),
        AdminInvitation.expires_at > utc_now()).limit(1)) is not None


def ensure_local_bootstrap_key():
    """Output an initial key on the dev terminal, once per active key lifetime."""
    if db.session.scalar(select(func.count(User.id)).where(User.role == "admin")):
        return None
    if active_bootstrap_exists():
        return None
    key = issue_key(bootstrap=True, minutes=60)
    print("\n" + "=" * 62 + "\nCSTBS INITIAL ADMIN REGISTRATION (LOCAL DEVELOPMENT)\n"
          "Open http://127.0.0.1:5000/register/admin\n"
          f"ONE-TIME KEY: {key}\n"
          "Expires in 60 minutes. Never share this key or commit logs.\n"
          "If lost, run: python -m flask --app run.py reset-bootstrap-key\n"
          + "=" * 62 + "\n", flush=True)
    return key


def find_valid_invitation(key):
    """Find by keyed fingerprint, never by comparing plaintext stored secrets."""
    return db.session.scalar(select(AdminInvitation).where(
        AdminInvitation.token_hash == _fingerprint(key),
        AdminInvitation.used_at.is_(None),
        AdminInvitation.expires_at > utc_now()).limit(1))


def consume_invitation(invite, new_user_id):
    """Atomic consume prevents two concurrent successful uses of one key."""
    if invite.bootstrap and db.session.scalar(select(func.count(User.id)).where(
            User.role == "admin", User.id != new_user_id)):
        return False
    result = db.session.execute(update(AdminInvitation).where(
        AdminInvitation.id == invite.id, AdminInvitation.used_at.is_(None),
        AdminInvitation.expires_at > utc_now()).values(
            used_at=utc_now(), used_by_id=new_user_id))
    return result.rowcount == 1


def revoke_unused_bootstrap():
    db.session.execute(update(AdminInvitation).where(
        AdminInvitation.bootstrap.is_(True), AdminInvitation.used_at.is_(None)
    ).values(used_at=utc_now()))
