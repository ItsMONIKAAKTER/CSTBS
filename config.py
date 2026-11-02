"""Application configuration, with secrets supplied by the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Default settings for the Version 1 local prototype."""

    SECRET_KEY = os.getenv("SECRET_KEY")
    # Flask-SQLAlchemy resolves relative SQLite paths under app.instance_path.
    SQLALCHEMY_DATABASE_URI = "sqlite:///cstbs.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
