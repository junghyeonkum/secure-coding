import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def get_secret_key():
    secret_key = os.environ.get("SECRET_KEY")
    if secret_key:
        return secret_key
    if os.environ.get("FLASK_ENV") == "development" or os.environ.get("FLASK_DEBUG") == "1":
        return secrets.token_hex(32)
    raise RuntimeError("SECRET_KEY environment variable is required.")


class Config:
    SECRET_KEY = get_secret_key()
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'secure_market.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        str(BASE_DIR / "app" / "static" / "uploads"),
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    WTF_CSRF_TIME_LIMIT = 3600
    DEBUG = os.environ.get("FLASK_ENV") == "development" and (
        os.environ.get("FLASK_DEBUG", "1") != "0"
    )
    SSL_CONTEXT = "adhoc" if os.environ.get("FLASK_ADHOC_SSL", "false").lower() == "true" else None
