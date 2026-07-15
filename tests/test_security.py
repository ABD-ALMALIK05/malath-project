import time

from malath.security import PIN_VERIFIED_AT_SESSION_KEY
from malath.services.storage import StorageError

from .conftest import get_csrf_token, login, upload_document


def test_registration_enforces_password_policy(client):
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
    )

    assert "Password must be at least 8 characters" in response.get_data(as_text=True)


def test_csrf_rejects_missing_token(client):
    response = client.post("/login", data={"identifier": "alice", "password": "Password1"})

    assert response.status_code == 400
    assert "form could not be verified" in response.get_data(as_text=True)


def test_login_rejects_external_next_redirect(client, registered_user):
    response = login(client, path="/login?next=https://example.org/phish")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard?lang=en")


def test_login_allows_local_next_redirect(client, registered_user):
    response = login(client, path="/login?next=/dashboard?lang=ar")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard?lang=ar")


def test_expired_pin_requires_reverification(logged_in_client):
    with logged_in_client.session_transaction() as session:
        session[PIN_VERIFIED_AT_SESSION_KEY] = time.time() - 120

    response = logged_in_client.get("/documents")

    assert response.status_code == 302
    assert "/verify-pin" in response.headers["Location"]


def test_login_rate_limit_is_deterministic(app, client, registered_user):
    app.config["RATE_LIMIT_DEFAULT"] = 1

    first = login(client, password="WrongPassword1")
    second = login(client, password="WrongPassword1")

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Too many attempts" in second.get_data(as_text=True)


def test_storage_exception_details_are_not_exposed(
    pin_verified_client, valid_pdf_upload, monkeypatch
):
    def fail_upload(*args, **kwargs):
        raise StorageError("internal path and bucket details")

    monkeypatch.setattr("malath.documents.routes.save_fileobj", fail_upload)
    content, filename = valid_pdf_upload
    response = upload_document(pin_verified_client, content, filename)
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "could not be uploaded" in body
    assert "internal path" not in body
    assert "bucket details" not in body


def test_internal_error_hides_exception_details(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/test-error")
    def test_error():
        raise RuntimeError("private internal detail")

    response = client.get("/test-error?lang=en")
    body = response.get_data(as_text=True)

    assert response.status_code == 500
    assert "An unexpected error occurred." in body
    assert "private internal detail" not in body
