import io
import time

from malath.extensions import db
from malath.models import Document
from malath.security import PIN_VERIFIED_AT_SESSION_KEY
from malath.services.storage import StorageError

from .conftest import create_user, get_csrf_token, login, mark_pin_verified


def test_registration_enforces_password_policy(client, app):
    token = get_csrf_token(client, "/register")

    response = client.post(
        "/register",
        data={
            "full_name": "Weak Password",
            "username": "weak",
            "email": "weak@example.com",
            "password": "short",
            "pin": "123456",
            "csrf_token": token,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Password must be at least 8 characters" in response.get_data(as_text=True)


def test_csrf_rejects_missing_token(client):
    response = client.post("/login", data={"identifier": "alice", "password": "Password1"})

    assert response.status_code == 400
    assert "form could not be verified" in response.get_data(as_text=True)


def test_login_rejects_external_next_redirect(client, app):
    with app.app_context():
        create_user()

    response = login(client, path="/login?next=https://example.org/phish")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard?lang=en")


def test_unauthenticated_dashboard_requires_login(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_expired_pin_verification_requires_reverification(client, app):
    with app.app_context():
        create_user()

    login(client)
    with client.session_transaction() as session:
        session[PIN_VERIFIED_AT_SESSION_KEY] = time.time() - 120

    response = client.get("/documents")

    assert response.status_code == 302
    assert "/verify-pin" in response.headers["Location"]


def test_document_ownership_is_filtered_before_download(client, app):
    with app.app_context():
        create_user(username="alice", email="alice@example.com")
        owner = create_user(username="bob", email="bob@example.com")
        document = Document(
            title="Private",
            category="personal",
            description="",
            file_url="https://example.invalid/private.pdf",
            stored_filename="users/2/personal/private.pdf",
            original_filename="private.pdf",
            file_type="pdf",
            file_size=16,
            user_id=owner.id,
        )
        db.session.add(document)
        db.session.commit()
        document_id = document.id

    login(client)
    mark_pin_verified(client)

    response = client.get(f"/documents/download/{document_id}")

    assert response.status_code == 404


def test_logout_requires_post_and_clears_session(client, app):
    with app.app_context():
        create_user()

    login(client)

    assert client.get("/logout").status_code == 405

    token = get_csrf_token(client, "/dashboard")
    response = client.post("/logout", data={"csrf_token": token}, follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert client.get("/dashboard").status_code == 302


def test_storage_exception_text_is_not_exposed(client, app, monkeypatch):
    with app.app_context():
        create_user()

    login(client)
    mark_pin_verified(client)

    def fail_upload(*args, **kwargs):
        raise StorageError("internal /srv/app path and bucket details")

    monkeypatch.setattr("malath.documents.routes.upload_fileobj", fail_upload)

    token = get_csrf_token(client, "/upload")
    response = client.post(
        "/upload",
        data={
            "title": "Passport",
            "category": "personal",
            "description": "",
            "file": (io.BytesIO(b"%PDF-1.4\n"), "passport.pdf"),
            "csrf_token": token,
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "could not be uploaded" in body
    assert "internal /srv/app" not in body
    assert "bucket details" not in body
