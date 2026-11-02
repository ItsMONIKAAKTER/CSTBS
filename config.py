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

    # Console backend prints development messages through the Flask logger.
    # Set MAIL_BACKEND=smtp and supply Ethereal SMTP credentials to send mail.
    MAIL_BACKEND = os.getenv("MAIL_BACKEND", "console").lower()
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.ethereal.email")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in ("true", "1", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "CSTBS <no-reply@campus.example>")
    MAIL_SUPPRESS_SEND = os.getenv("MAIL_SUPPRESS_SEND", "false").lower() in ("true", "1", "yes")
