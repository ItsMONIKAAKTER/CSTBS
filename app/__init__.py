"""CSTBS application factory, extensions, and safe local management commands."""

from pathlib import Path
import sqlite3

import click
from flask import Flask, render_template
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError
from sqlalchemy import select, event as sqla_event
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
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
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

    from .models import User  # Register all SQLAlchemy models.
    from .routes import main
    from .admin import admin
    from .reports import reports

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
        db.create_all()
        upgrade_v1_user_schema()
        upgrade_v2_booking_constraints()
        upgrade_v3_seat_blocking()
        backfill_empty_event_seats()

    if app.config.get("APP_ENV") != "production":
        with app.app_context():
            initialize_schema()

    @app.cli.command("init-db")
    def init_db_command():
        """Explicit database initialization for deployment and fresh installs."""
        initialize_schema()
        click.echo("Database schema initialized. Check backup/migration requirements.")

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

    @app.cli.command("set-role")
    @click.argument("email")
    @click.argument("role", type=click.Choice(["student", "staff", "admin"]))
    def set_role_command(email, role):
        """Assign an account's role locally, never through public registration."""
        normalized_email = email.strip().lower()
        user = db.session.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            raise click.ClickException("No user found. Register the account first.")
        user.role = role
        db.session.commit()
        click.echo(f"Updated {normalized_email} to role: {role}")

    return app
