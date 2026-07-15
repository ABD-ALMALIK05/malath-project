import pytest

from malath.models import User
from malath.security import PIN_VERIFIED_AT_SESSION_KEY

from .conftest import get_csrf_token, login


def registration_data(**overrides):
    data = {
        "full_name": "New User",
        "username": "newuser",
        "email": "new@example.com",
        "password": "Password1",
        "pin": "123456",
    }
    data.update(overrides)
    return data


def register(client, **overrides):
    data = registration_data(**overrides)
    data["csrf_token"] = get_csrf_token(client, "/register")
    return client.post("/register", data=data, follow_redirects=False)


def test_registration_creates_hashed_credentials(client, app):
    response = register(client)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    user = User.query.one()
    assert user.username == "newuser"
    assert user.password_hash != "Password1"
    assert user.pin_hash != "123456"
    assert user.check_password("Password1")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"username": "alice", "email": "different@example.com"}, "Username already exists"),
        ({"username": "different", "email": "alice@example.com"}, "Email already exists"),
    ],
)
def test_registration_rejects_duplicate_identity(client, registered_user, overrides, message):
    response = register(client, **overrides)

    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert User.query.count() == 1


@pytest.mark.parametrize("identifier", ["alice", "alice@example.com"])
def test_login_accepts_username_or_email(client, registered_user, identifier):
    response = login(client, identifier=identifier)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard?lang=en")


def test_invalid_login_does_not_authenticate(client, registered_user):
    response = login(client, password="WrongPassword1")

    assert response.status_code == 200
    assert "Invalid username/email or password" in response.get_data(as_text=True)
    assert client.get("/dashboard").status_code == 302


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_valid_pin_unlocks_document_area(logged_in_client):
    token = get_csrf_token(logged_in_client, "/verify-pin")
    response = logged_in_client.post(
        "/verify-pin",
        data={"pin": "123456", "csrf_token": token},
        follow_redirects=False,
    )

    assert response.status_code == 302
    with logged_in_client.session_transaction() as session:
        assert PIN_VERIFIED_AT_SESSION_KEY in session


@pytest.mark.parametrize("pin", ["12345", "999999"])
def test_invalid_pin_does_not_unlock_documents(logged_in_client, pin):
    token = get_csrf_token(logged_in_client, "/verify-pin")
    response = logged_in_client.post(
        "/verify-pin",
        data={"pin": pin, "csrf_token": token},
    )

    assert response.status_code == 200
    with logged_in_client.session_transaction() as session:
        assert PIN_VERIFIED_AT_SESSION_KEY not in session


def test_logout_is_post_only_and_clears_login(logged_in_client):
    assert logged_in_client.get("/logout").status_code == 405

    token = get_csrf_token(logged_in_client, "/dashboard")
    response = logged_in_client.post("/logout", data={"csrf_token": token})

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert logged_in_client.get("/dashboard").status_code == 302
