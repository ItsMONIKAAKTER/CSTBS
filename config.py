"""Configuration for CSTBS; sensitive settings come from the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Development defaults; override settings through create_app if testing."""

    SECRET_KEY = os.getenv("SECRET_KEY")
    # Relative SQLite paths are resolved inside the Flask instance directory.
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cstbs.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set SESSION_COOKIE_SECURE=True when deploying behind HTTPS.
