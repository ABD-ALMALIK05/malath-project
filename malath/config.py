import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'malath.db').as_posix()}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or os.urandom(32)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_BUCKET_NAME = os.getenv("AWS_S3_BUCKET")
    AWS_REGION = os.getenv("AWS_REGION")

    UPLOAD_FOLDER = os.getenv("LOCAL_STORAGE_PATH", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
