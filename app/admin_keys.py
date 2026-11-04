"""20-minute, one-time administrator activation and recovery keys.

A key is bound to one existing admin account; no public admin registration or
implicit privilege escalation. Only HMAC fingerprints are stored in SQLite.
The plaintext key exists only in terminal output or one protected admin page.
"""

from datetime import timedelta
import hashlib
import hmac
import re
import secrets

from flask import current_app
from sqlalchemy import func, select, update

from . import db
from .models import AdminInvitation, User, utc_now

KEY_MINUTES = 20
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value):
    email = (value or "").strip().lower()
    if len(email) > 254 or not _EMAIL.fullmatch(email):
        raise ValueError("Enter a valid administrator email address.")
    return email


def _fingerprint(key):
    secret = current_app.config["SECRET_KEY"].encode("utf-8")
    return hmac.new(secret, key.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def issue_login_key(admin_user, *, created_by=None, minutes=KEY_MINUTES, bootstrap=False):
    """Issue a password-activation/reset key; revoke existing password sessions."""
    if admin_user is None or admin_user.id is None or admin_user.role != "admin":
        raise ValueError("Keys can be issued only to existing administrators.")
    if not 1 <= minutes <= 20:
        raise ValueError("The key lifetime must be at most 20 minutes.")
    now = utc_now()
    db.session.execute(update(AdminInvitation).where(
        AdminInvitation.target_user_id == admin_user.id,
        AdminInvitation.used_at.is_(None)
    ).values(used_at=now))
    # Issuing a key revokes password sessions until activation finishes.
    admin_user.password_ready = False
    admin_user.auth_version = (admin_user.auth_version or 0) + 1
    key = "CSTBS-" + secrets.token_urlsafe(24)
    row = AdminInvitation(
        token_hash=_fingerprint(key), bootstrap=bootstrap,
        target_user_id=admin_user.id, created_by_id=created_by,
        expires_at=now + timedelta(minutes=minutes))
    db.session.add(row)
    db.session.commit()
    return key


def consume_login_key(email, key, new_password=None):
    """Atomically redeem a still-valid key for its exact admin email.

    Password and used_at are committed atomically before login.
    Never creates users or changes roles.
    """
    try:
        normalized = normalize_email(email)
    except ValueError:
        return None
    if not isinstance(key, str) or not 20 <= len(key) <= 160:
        return None
    user = db.session.scalar(select(User).where(
        User.email == normalized, User.role == "admin"
    ))
    if user is None:
        return None
    now = utc_now()
    invitation_id = db.session.scalar(select(AdminInvitation.id).where(
        AdminInvitation.token_hash == _fingerprint(key),
        AdminInvitation.target_user_id == user.id,
        AdminInvitation.used_at.is_(None),
        AdminInvitation.expires_at > now
    ).limit(1))
    if invitation_id is None:
        return None
    claimed = db.session.execute(update(AdminInvitation).where(
        AdminInvitation.id == invitation_id,
        AdminInvitation.target_user_id == user.id,
        AdminInvitation.used_at.is_(None),
        AdminInvitation.expires_at > utc_now()
    ).values(used_at=utc_now(), used_by_id=user.id))
    if claimed.rowcount != 1:
        db.session.rollback()
        return None
    if not isinstance(new_password, str) or not 12 <= len(new_password) <= 128:
        db.session.rollback()
        return None
    user.set_password(new_password)
    db.session.commit()
    return user


def provision_first_admin(email, full_name="University Administrator"):
    """Create the very first admin only from a trusted local terminal command."""
    email = normalize_email(email)
    if db.session.scalar(select(func.count(User.id)).where(User.role == "admin")):
        raise ValueError("An administrator already exists. Use an existing admin account.")
    if db.session.scalar(select(User.id).where(User.email == email)) is not None:
        raise ValueError("Email already belongs to an account. Choose a different email.")
    name = full_name.strip()
    if not 2 <= len(name) <= 120:
        raise ValueError("Name must be 2 to 120 characters.")
    user = User(full_name=name, email=email, role="admin")
    # Give an unusable random hash until the admin activates with a key.
    user.set_password(secrets.token_urlsafe(48))
    user.password_ready = False  # One-time activation sets the real password.
    db.session.add(user)
    db.session.commit()
    return user


def print_terminal_login_key(user, *, bootstrap=False):
    key = issue_login_key(user, bootstrap=bootstrap)
    print("\n" + "=" * 66 + "\n"
          "CSTBS ADMIN ACTIVATION KEY - LOCAL TERMINAL\n"
          f"Administrator: {user.email}\n"
          f"ONE-TIME KEY: {key}\n"
          "Valid: 20 minutes | One activation only\n"
          "Open: http://127.0.0.1:5000/admin/activate\n"
          "This key is already stored securely. Do not edit any file.\n"
          "If it expires: python -m flask --app run.py admin-key EMAIL\n"
          + "=" * 66 + "\n", flush=True)
    return key
