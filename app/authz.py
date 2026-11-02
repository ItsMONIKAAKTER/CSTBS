"""Centralized authorization for administrative routes."""

from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(view):
    """Deny non-administrators with HTTP 403 (use after @login_required)."""
    @wraps(view)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return decorated
