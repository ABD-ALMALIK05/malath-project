from malath.extensions import db
from malath.models import Document

from .conftest import create_user, get_csrf_token, login, mark_pin_verified


def test_public_pages_render_correct_language_direction_and_landmarks(client):
    english = client.get("/?lang=en").get_data(as_text=True)
    arabic = client.get("/?lang=ar").get_data(as_text=True)

    assert '<html lang="en" dir="ltr">' in english
    assert '<html lang="ar" dir="rtl">' in arabic
    assert 'href="#main-content"' in english
    assert 'id="main-content"' in arabic


def test_language_switch_preserves_endpoint_and_query(client):
    body = client.get("/login?lang=en&next=/documents").get_data(as_text=True)

    assert "lang=ar" in body
    assert "next=/documents" in body or "next=%2Fdocuments" in body


def test_registration_validation_preserves_safe_values_only(client):
    token = get_csrf_token(client, "/register")

    response = client.post(
        "/register",
        data={
            "full_name": "Weak Password",
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "short",
            "pin": "123456",
            "csrf_token": token,
        },
    )
    body = response.get_data(as_text=True)

    assert 'value="Weak Password"' in body
    assert 'value="weakuser"' in body
    assert 'value="weak@example.com"' in body
    assert 'value="short"' not in body
    assert 'value="123456"' not in body


def test_upload_validation_preserves_non_sensitive_values(client, app):
    with app.app_context():
        create_user()
    login(client)
    mark_pin_verified(client)
    token = get_csrf_token(client, "/upload")

    response = client.post(
        "/upload",
        data={
            "title": "Passport",
            "category": "government",
            "description": "Keep current copy",
            "csrf_token": token,
        },
    )
    body = response.get_data(as_text=True)

    assert 'value="Passport"' in body
    assert "Keep current copy" in body
    assert 'value="government" selected' in body


def test_document_list_displays_human_metadata(client, app):
    with app.app_context():
        user = create_user()
        document = Document(
            title="Insurance",
            category="medical",
            description="Clinic records",
            file_url="users/1/medical/insurance.pdf",
            stored_filename="users/1/medical/insurance.pdf",
            original_filename="insurance.pdf",
            file_type="pdf",
            file_size=1536,
            user_id=user.id,
        )
        db.session.add(document)
        db.session.commit()

    login(client)
    mark_pin_verified(client)
    body = client.get("/documents?lang=en").get_data(as_text=True)

    assert "Medical" in body
    assert "1.5 KB" in body
    assert "insurance.pdf" in body
