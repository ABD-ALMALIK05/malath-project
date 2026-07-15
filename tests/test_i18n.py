from malath.extensions import db
from malath.i18n import category_label, format_file_size, format_upload_date
from malath.models import Document

from .conftest import get_csrf_token


def test_public_pages_render_language_direction_and_landmarks(client):
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


def test_registration_validation_preserves_only_safe_values(client):
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


def test_document_list_displays_localized_human_metadata(pin_verified_client, registered_user):
    document = Document(
        title="Insurance",
        category="medical",
        description="Clinic records",
        file_url="users/1/medical/insurance.pdf",
        stored_filename="users/1/medical/insurance.pdf",
        original_filename="insurance.pdf",
        file_type="pdf",
        file_size=1536,
        user_id=registered_user.id,
    )
    db.session.add(document)
    db.session.commit()

    body = pin_verified_client.get("/documents?lang=en").get_data(as_text=True)

    assert "Medical" in body
    assert "1.5 KB" in body
    assert "insurance.pdf" in body


def test_translation_helpers_handle_fallback_values(app):
    with app.test_request_context("/?lang=en"):
        assert category_label("medical") == "Medical"
        assert category_label("custom") == "custom"
        assert format_file_size(None) == "0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_upload_date(None) == ""
