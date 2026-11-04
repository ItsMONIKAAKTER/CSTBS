"""Make long-lived Flask test contexts behave like independent HTTP requests.

A number of legacy CSTBS integration tests push one application context in
setUp and keep it active while making requests with multiple test clients.
Flask's `g` is scoped to that context. Without isolation, Flask-Login caches
the wrong client user and Flask-WTF reuses stale signed CSRF tokens after
login clears the session. Real HTTP requests each receive a fresh context.

Do not disable CSRF or role authorization in tests.
"""

from flask import g

from app import create_app


def create_isolated_test_app(config):
    """Create a fully protected app with independent request-local caches."""
    app = create_app(config)

    def _reset_request_local_cache():
        # Reset BEFORE the Flask-WTF CSRFProtect before-request callback runs.
        # With ordinary HTTP traffic a fresh app context makes this automatic.
        for key in ("csrf_token", "csrf_valid", "_login_user"):
            g.pop(key, None)

    app.before_request_funcs.setdefault(None, []).insert(0, _reset_request_local_cache)
    return app
