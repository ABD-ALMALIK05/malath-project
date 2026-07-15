import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

from .security import get_pin_verification_minutes, get_secret_key, get_session_cookie_secure

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'malath.db').as_posix()}"


class Config:
    SECRET_KEY = get_secret_key()
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()
    LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH", str(BASE_DIR / "uploads"))

    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_BUCKET_NAME = os.getenv("AWS_S3_BUCKET")
    AWS_REGION = os.getenv("AWS_REGION")
    S3_PRESIGNED_EXPIRES_SECONDS = int(os.getenv("S3_PRESIGNED_EXPIRES_SECONDS", "300"))

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = get_session_cookie_secure()
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    PIN_VERIFICATION_MINUTES = get_pin_verification_minutes()
    CSRF_ENABLED = os.getenv("CSRF_ENABLED", "true").lower() != "false"
    RATE_LIMIT_DEFAULT = int(os.getenv("RATE_LIMIT_DEFAULT", "5"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "300"))
