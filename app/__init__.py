"""CSTBS application factory, extensions, and safe local management commands."""

from pathlib import Path

import click
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import select

from config import Config

# Extensions are constructed once and bound to each application instance.
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()


def create_app(test_config=None):
    """Configure the Flask application and initialize its SQLite schema."""
    instance_dir = Path(__file__).resolve().parent.parent / "instance"
    app = Flask(__name__, instance_path=str(instance_dir), instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if app.config.get("SECRET_KEY") in (None, "", "replace-with-a-random-secret"):
        raise RuntimeError("Set a strong SECRET_KEY in .env before starting CSTBS.")

    instance_dir.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    from .models import User  # Register all SQLAlchemy models.
    from .routes import main
    from .admin import admin

    @login_manager.user_loader
    def load_user(user_id):
        """Resolve Flask-Login session IDs without trusting external input."""
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    app.register_blueprint(main)
    app.register_blueprint(admin)

    with app.app_context():
        db.create_all()  # Convenient for local SQLite; not a full migration system.
        from .migrations import upgrade_v1_user_schema, upgrade_v2_booking_constraints, upgrade_v3_seat_blocking
        from .seating import backfill_empty_event_seats

        upgrade_v1_user_schema()
        upgrade_v2_booking_constraints()
        upgrade_v3_seat_blocking()
        backfill_empty_event_seats()

    @app.cli.command("seed-events")
    def seed_events_command():
        """Add the sample events if the catalog has no entries."""
        from .seed import seed_demo_events

        count = seed_demo_events()
        click.echo(f"Seeded {count} sample event(s), each with 60 seats.")

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
