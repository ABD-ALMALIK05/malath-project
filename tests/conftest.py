import io
import re
import time

import pytest
from PIL import Image

from malath import create_app
from malath.extensions import db
from malath.models import User
from malath.security import PIN_VERIFIED_AT_SESSION_KEY, reset_rate_limits


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = True
    CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PIN_VERIFICATION_MINUTES = 1
    RATE_LIMIT_DEFAULT = 100
    RATE_LIMIT_WINDOW_SECONDS = 60
    STORAGE_BACKEND = "local"
    S3_PRESIGNED_EXPIRES_SECONDS = 300
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    AWS_ACCESS_KEY = "test"
    AWS_SECRET_KEY = "test"
    AWS_BUCKET_NAME = "test-bucket"
    AWS_REGION = "eu-north-1"


@pytest.fixture
def app(tmp_path):
    class Config(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        LOCAL_STORAGE_PATH = str(tmp_path / "uploads")

    reset_rate_limits()
    app = create_app(Config)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
    reset_rate_limits()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def database(app):
    return db


@pytest.fixture
def registered_user(app):
    return create_user()


@pytest.fixture
def logged_in_client(client, registered_user):
    response = login(client)
    assert response.status_code == 302
    return client


@pytest.fixture
def pin_verified_client(logged_in_client):
    mark_pin_verified(logged_in_client)
    return logged_in_client


@pytest.fixture
def valid_pdf_upload():
    return pdf_upload_bytes(), "document.pdf"


@pytest.fixture
def valid_image_upload():
    return image_upload_bytes(), "document.png"


def extract_csrf_token(response):
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def get_csrf_token(client, path):
    return extract_csrf_token(client.get(path))


def create_user(username="alice", email="alice@example.com", password="Password1", pin="123456"):
    user = User(full_name="Test User", username=username, email=email)
    user.set_password(password)
    user.set_pin(pin)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, identifier="alice", password="Password1", path="/login"):
    token = get_csrf_token(client, path)
    return client.post(
        path,
        data={"identifier": identifier, "password": password, "csrf_token": token},
        follow_redirects=False,
    )


def mark_pin_verified(client):
    with client.session_transaction() as session:
        session[PIN_VERIFIED_AT_SESSION_KEY] = time.time()


def pdf_upload_bytes():
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def image_upload_bytes(image_format="PNG"):
    image = Image.new("RGB", (2, 2), color=(194, 31, 48))
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def upload_document(
    client,
    content,
    filename,
    *,
    title="Passport",
    category="personal",
    description="Travel document",
    follow_redirects=True,
):
    token = get_csrf_token(client, "/upload")
    return client.post(
        "/upload",
        data={
            "title": title,
            "category": category,
            "description": description,
            "file": (io.BytesIO(content), filename),
            "csrf_token": token,
        },
        content_type="multipart/form-data",
        follow_redirects=follow_redirects,
    )
