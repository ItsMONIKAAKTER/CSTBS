"""Flask application factory and extension setup."""

from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()


def create_app(test_config=None):
    """Create the app, initialize SQLite, and load demo events."""
    instance_dir = Path(__file__).resolve().parent.parent / "instance"
    app = Flask(
        __name__, instance_path=str(instance_dir), instance_relative_config=True
    )
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if app.config.get("SECRET_KEY") in (None, "", "replace-with-a-random-secret"):
        raise RuntimeError(
            "Set SECRET_KEY in .env before starting. See README.md for instructions."
        )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    from . import models  # noqa: F401 - registers SQLAlchemy models
    from .routes import main

    app.register_blueprint(main)

    with app.app_context():
        db.create_all()  # Development-only initialization; not a migration system.
        from .seed import seed_demo_events

        seed_demo_events()

    return app
