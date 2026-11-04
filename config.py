"""Environment-based configuration for CSTBS (Python 3.10+)."""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def local_development_secret():
    """Keep a stable, private local secret without requiring edits to .env.

    This is never used in production. The instance directory is ignored by Git.
    """
    secret_path = BASE_DIR / "instance" / ".local_secret_key"
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    if not secret_path.exists():
        try:
            fd = os.open(str(secret_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(secrets.token_hex(32))
        except FileExistsError:
            pass  # Another local process initialized the same application.
    return secret_path.read_text(encoding="utf-8").strip()


def configured_secret():
    configured = os.getenv("SECRET_KEY", "").strip()
    if configured and configured != "replace-with-a-random-secret":
        return configured
    if os.getenv("APP_ENV", "development").lower() == "production":
        return None
    return local_development_secret()


def env_boolean(name, default=False):
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


class Config:
    """Local defaults with explicit production-facing security settings."""

    APP_ENV = os.getenv("APP_ENV", "development").lower()
    SECRET_KEY = configured_secret()
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///cstbs.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 15}} if SQLALCHEMY_DATABASE_URI.startswith("sqlite:") else {}
    MAX_CONTENT_LENGTH = 128 * 1024  # Forms never need large uploads.
    MAX_FORM_MEMORY_SIZE = 64 * 1024
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_boolean("SESSION_COOKIE_SECURE", APP_ENV == "production")
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PREFERRED_URL_SCHEME = "https" if APP_ENV == "production" else "http"
    TRUSTED_HOSTS = [host.strip() for host in os.getenv("TRUSTED_HOSTS", "").split(",") if host.strip()] or None
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    # Console mode prints sensitive booking details to restricted application logs.
    MAIL_BACKEND = os.getenv("MAIL_BACKEND", "console").lower()
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.ethereal.email")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = env_boolean("MAIL_USE_TLS", True)
    MAIL_USE_SSL = env_boolean("MAIL_USE_SSL", False)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "CSTBS <no-reply@campus.example>")
    MAIL_SUPPRESS_SEND = env_boolean("MAIL_SUPPRESS_SEND", False)
