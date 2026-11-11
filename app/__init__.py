"""CSTBS application factory, extensions, and safe local management commands."""

from pathlib import Path
import sqlite3

import click
from flask import Flask, render_template, redirect, request, url_for
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy import select, func, event as sqla_event
from sqlalchemy.engine import Engine

from config import Config

# Extensions are constructed once and bound to each application instance.
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
# Local development uses in-memory limits. Configure Redis for multiworker use.
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])


@sqla_event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    """SQLite does not enforce foreign keys unless explicitly enabled."""
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(test_config=None):
    """Configure the Flask application and initialize its SQLite schema."""
    instance_dir = Path(__file__).resolve().parent.parent / "instance"
    app = Flask(__name__, instance_path=str(instance_dir), instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if app.config.get("SECRET_KEY") in (None, "", "replace-with-a-random-secret"):
        raise RuntimeError("Set a strong SECRET_KEY in .env before starting CSTBS.")
    if app.config.get("APP_ENV") == "production":
        if len(app.config["SECRET_KEY"]) < 32:
            raise RuntimeError("Production SECRET_KEY must contain at least 32 characters.")
        if not app.config.get("SESSION_COOKIE_SECURE"):
            raise RuntimeError("Production sessions must use HTTPS-only cookies.")
        if not app.config.get("TICKET_SIGNING_KEY") or len(app.config["TICKET_SIGNING_KEY"]) < 32:
            raise RuntimeError("Set a persistent TICKET_SIGNING_KEY for production QR validity.")
        if not app.config.get("TRUSTED_HOSTS"):
            raise RuntimeError("Set TRUSTED_HOSTS before production deployment.")
        if app.config.get("RATELIMIT_STORAGE_URI", "memory://") == "memory://":
            raise RuntimeError("Set shared RATELIMIT_STORAGE_URI (e.g., Redis) in production.")
        if app.config.get("MAIL_BACKEND") != "smtp":
            raise RuntimeError("Configure MAIL_BACKEND=smtp for production email.")

    instance_dir.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    if app.config.get("TESTING") and (not test_config or "RATELIMIT_ENABLED" not in test_config):
        app.config["RATELIMIT_ENABLED"] = False
    limiter.init_app(app)

    @app.after_request
    def add_security_headers(response):
        """Security headers for dynamic HTML and downloads; no inline scripts."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        if app.config.get("APP_ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    @app.before_request
    def invalidate_old_admin_sessions():
        """Revoke admin sessions after password activation/reset or role change."""
        from flask_login import current_user, logout_user
        from flask import session
        if current_user.is_authenticated and current_user.role == "admin":
            if (not current_user.password_ready or
                    session.get("admin_auth_version") != current_user.auth_version):
                logout_user()
                session.pop("admin_auth_version", None)

    @login_manager.unauthorized_handler
    def login_required_handler():
        """Send anonymous visitors to role-appropriate login pages."""
        if request.path.startswith("/admin/"):
            return redirect(url_for("main.admin_login"))
        return redirect(url_for("main.login", next=request.full_path))

    from .models import User, AdminInvitation, Ticket, Gate  # Register all SQLAlchemy models.
    from .routes import main
    from .admin import admin
    from .reports import reports
    from .entry import entry

    @login_manager.user_loader
    def load_user(user_id):
        """Resolve Flask-Login session IDs without trusting external input."""
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(reports)
    app.register_blueprint(entry)

    @app.get("/health")
    def health():
        from flask import jsonify
        try:
            db.session.execute(select(1)).scalar_one()
        except Exception:
            return jsonify(status="unavailable"), 503
        return jsonify(status="ok", version="5.4")

    @app.errorhandler(CSRFError)
    def handle_csrf_error(_error):
        """Friendly response without exposing internal token validation details."""
        return render_template("error.html", code=400, heading="Please refresh this form",
            explanation="The form expired or could not be verified. Reload the page and try again."), 400

    @app.errorhandler(403)
    def handle_forbidden(_error):
        return render_template("error.html", code=403, heading="Access restricted",
            explanation="You do not have permission to view this page."), 403

    @app.errorhandler(404)
    def handle_not_found(_error):
        return render_template("error.html", code=404, heading="Page not found",
            explanation="The resource you requested does not exist."), 404

    @app.errorhandler(413)
    def handle_too_large(_error):
        return render_template("error.html", code=413, heading="Request or export too large",
            explanation="Reduce the size of your request or narrow the report filters."), 413

    @app.errorhandler(429)
    def handle_rate_limit(_error):
        return render_template("error.html", code=429, heading="Too many requests",
            explanation="Please reduce request frequency and try again after the limit resets."), 429

    def initialize_schema():
        """Initialize a fresh SQLite DB or apply V1-V4 compatibility updates.

        This is intentionally limited and is NOT a replacement for a reviewed
        Alembic migration plan in a larger production deployment.
        """
        from .migrations import (
            upgrade_v1_user_schema, upgrade_v2_booking_constraints,
            upgrade_v3_seat_blocking,
        )
        from .seating import backfill_empty_event_seats
        from .migrations_v51 import upgrade_v51
        from .migrations_v52 import upgrade_v52
        from .migrations_v53 import upgrade_v53
        from .migrations_v54 import upgrade_v54
        from .backups import sqlite_backup
        # Backup legacy V5.2 DB before any schema changes, or abort on failure.
        sqlite_backup(version_guard=True) if db.engine.dialect.name == "sqlite" else None
        db.create_all()
        upgrade_v1_user_schema()
        upgrade_v2_booking_constraints()
        upgrade_v3_seat_blocking()
        upgrade_v51()
        upgrade_v52()
        upgrade_v53()
        upgrade_v54()
        backfill_empty_event_seats()

    if app.config.get("APP_ENV") != "production":
        with app.app_context():
            initialize_schema()

    @app.cli.command("init-db")
    def init_db_command():
        """Explicit database initialization for deployment and fresh installs."""
        initialize_schema()
        click.echo("Database schema initialized. Check backup/migration requirements.")

    @app.cli.command("backup-db")
    def backup_db_command():
        """Consistent SQLite backup under private instance/backups folder."""
        from .backups import sqlite_backup
        try:
            result = sqlite_backup()
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(str(result) if result else "No on-disk SQLite DB to back up.")

    @app.cli.command("seed-events")
    def seed_events_command():
        """Add the sample events if the catalog has no entries."""
        from .seed import seed_demo_events

        count = seed_demo_events()
        click.echo(f"Seeded {count} sample event(s), each with 60 seats.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Create optional demo accounts, bookings and seat blocks locally."""
        from .seed import seed_demo_environment
        try:
            result = seed_demo_environment()
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(result)

    @app.cli.command("admin-setup")
    @click.option("--email", prompt="Administrator email", help="Email for first administrator")
    @click.option("--name", default="University Administrator", prompt="Administrator name")
    def admin_setup_command(email, name):
        """First admin provisioning: trusted operator CLI, no source/env edits."""
        from .admin_keys import provision_first_admin, print_terminal_login_key
        try:
            user = provision_first_admin(email, name)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        print_terminal_login_key(user, bootstrap=True)

    @app.cli.command("admin-reset")
    @click.argument("email")
    def admin_reset_command(email):
        """Revoke an admin password and issue a 20-minute recovery key."""
        from .admin_keys import normalize_email, print_terminal_login_key
        normalized = normalize_email(email)
        user = db.session.scalar(select(User).where(User.email == normalized, User.role == "admin"))
        if user is None:
            raise click.ClickException("No administrator with that email.")
        print_terminal_login_key(user)

    @app.cli.command("admin-key")
    @click.argument("email")
    def admin_key_command(email):
        """Issue an activation key to an admin who has no active password."""
        from .admin_keys import normalize_email, print_terminal_login_key
        try:
            normalized = normalize_email(email)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        user = db.session.scalar(select(User).where(
            User.email == normalized, User.role == "admin"))
        if user is None:
            raise click.ClickException("No admin with that email. Use admin-setup first, "
                                       "or promote a user in Admin > Users.")
        if user.password_ready:
            raise click.ClickException("Already activated. Use admin-reset EMAIL only if you need to revoke its password.")
        print_terminal_login_key(user)

    @app.cli.command("reset-bootstrap-key")
    def legacy_key_command():
        """Guide users of V5.1 to the new explicit admin key workflow."""
        raise click.ClickException("V5.3 uses admin-key EMAIL (pending activation), "
                                   "admin-reset EMAIL (password recovery), or admin-setup.")

    @app.cli.command("set-role")
    @click.argument("email")
    @click.argument("role", type=click.Choice(["student", "staff", "admin"]))
    def set_role_command(email, role):
        """Local operator role adjustment for recovery; no public escalation."""
        normalized_email = email.strip().lower()
        user = db.session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            raise click.ClickException("No user found.")
        if user.role == "admin" and role != "admin":
            admin_count = db.session.scalar(select(func.count(User.id)).where(User.role == "admin"))
            if admin_count <= 1:
                raise click.ClickException("Cannot demote the last administrator.")
        if role == "student" and not user.student_id:
            raise click.ClickException("A student needs a unique Student ID first.")
        if role == "admin" and user.role != "admin":
            import secrets
            user.set_password(secrets.token_urlsafe(48))
            user.password_ready = False
        user.role = role
        user.auth_version = (user.auth_version or 0) + 1
        db.session.commit()
        click.echo(f"Updated {normalized_email} to role: {role}")
        if role == "admin" and not user.password_ready:
            click.echo("Next: generate a 20-minute activation key with admin-key EMAIL.")

    return app
