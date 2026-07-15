import pytest

from malath.extensions import db
from malath.models import Document
from malath.services.storage import LocalStorage

from .conftest import create_user, get_csrf_token, upload_document


@pytest.mark.parametrize("category", ["government", "medical", "property", "personal"])
def test_upload_accepts_each_document_category(pin_verified_client, valid_pdf_upload, category):
    content, filename = valid_pdf_upload
    response = upload_document(
        pin_verified_client,
        content,
        filename,
        title=f"{category.title()} document",
        category=category,
    )

    assert response.status_code == 200
    assert Document.query.one().category == category


def test_invalid_file_is_rejected(pin_verified_client):
    response = upload_document(pin_verified_client, b"plain text", "notes.txt")

    assert response.status_code == 200
    assert "Only valid PDF" in response.get_data(as_text=True)
    assert Document.query.count() == 0


def test_spoofed_file_is_rejected(pin_verified_client):
    response = upload_document(pin_verified_client, b"not a real pdf", "fake.pdf")

    assert response.status_code == 200
    assert "Only valid PDF" in response.get_data(as_text=True)
    assert Document.query.count() == 0


def test_document_listing_and_category_filter(pin_verified_client, registered_user):
    for title, category in (("Passport", "government"), ("Scan", "medical")):
        db.session.add(
            Document(
                title=title,
                category=category,
                description="",
                file_url=f"users/1/{category}/{title}.pdf",
                stored_filename=f"users/1/{category}/{title}.pdf",
                original_filename=f"{title}.pdf",
                file_type="pdf",
                file_size=48,
                user_id=registered_user.id,
            )
        )
    db.session.commit()

    all_documents = pin_verified_client.get("/documents?lang=en").get_data(as_text=True)
    government = pin_verified_client.get("/documents?category=government&lang=en").get_data(
        as_text=True
    )

    assert "Passport" in all_documents
    assert "Scan" in all_documents
    assert "Passport" in government
    assert "Scan.pdf" not in government


def test_document_upload_edit_download_delete_lifecycle(app, pin_verified_client, valid_pdf_upload):
    content, filename = valid_pdf_upload
    upload_response = upload_document(pin_verified_client, content, filename, title="Passport")
    assert "Document uploaded successfully" in upload_response.get_data(as_text=True)

    document = Document.query.one()
    document_id = document.id
    storage_key = document.storage_key
    storage = LocalStorage(app.config["LOCAL_STORAGE_PATH"])
    assert storage.exists(storage_key)

    token = get_csrf_token(pin_verified_client, f"/documents/edit/{document_id}")
    edit_response = pin_verified_client.post(
        f"/documents/edit/{document_id}",
        data={
            "title": "Updated Passport",
            "category": "government",
            "description": "Current copy",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert "Updated Passport" in edit_response.get_data(as_text=True)
    assert Document.query.one().category == "government"

    download = pin_verified_client.get(f"/documents/download/{document_id}")
    assert download.status_code == 200
    assert download.data.startswith(b"%PDF-")
    assert filename in download.headers["Content-Disposition"]
    download.close()

    token = get_csrf_token(pin_verified_client, "/documents")
    delete_response = pin_verified_client.post(
        f"/documents/delete/{document_id}",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "Document deleted successfully" in delete_response.get_data(as_text=True)
    assert Document.query.count() == 0
    assert not storage.exists(storage_key)


def test_cross_user_document_routes_return_not_found(pin_verified_client):
    owner = create_user(username="bob", email="bob@example.com")
    document = Document(
        title="Private",
        category="personal",
        description="",
        file_url="users/2/personal/private.pdf",
        stored_filename="users/2/personal/private.pdf",
        original_filename="private.pdf",
        file_type="pdf",
        file_size=16,
        user_id=owner.id,
    )
    db.session.add(document)
    db.session.commit()

    assert pin_verified_client.get(f"/documents/download/{document.id}").status_code == 404
    assert pin_verified_client.get(f"/documents/edit/{document.id}").status_code == 404

    token = get_csrf_token(pin_verified_client, "/documents")
    response = pin_verified_client.post(
        f"/documents/delete/{document.id}", data={"csrf_token": token}
    )
    assert response.status_code == 404
    assert Document.query.filter_by(id=document.id).one()
