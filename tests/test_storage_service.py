import io

from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from malath.extensions import db
from malath.models import Document
from malath.services.storage import LocalStorage, StorageError

from .conftest import create_user, get_csrf_token, login, mark_pin_verified


def pdf_upload_bytes():
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def image_upload_bytes(image_format="PNG"):
    image = Image.new("RGB", (2, 2), color=(194, 31, 48))
    output = io.BytesIO()
    image.save(output, format=image_format)
    output.seek(0)
    return output.getvalue()


def authenticated_upload(client, filename, content, follow_redirects=True):
    token = get_csrf_token(client, "/upload")
    return client.post(
        "/upload",
        data={
            "title": "Passport",
            "category": "personal",
            "description": "Travel document",
            "file": (io.BytesIO(content), filename),
            "csrf_token": token,
        },
        content_type="multipart/form-data",
        follow_redirects=follow_redirects,
    )


def login_with_pin(client, app):
    with app.app_context():
        create_user()
    login(client)
    mark_pin_verified(client)


def test_local_pdf_upload_saves_private_file(client, app):
    login_with_pin(client, app)

    response = authenticated_upload(client, "passport.pdf", pdf_upload_bytes())

    assert response.status_code == 200
    with app.app_context():
        document = Document.query.one()
        storage = LocalStorage(app.config["LOCAL_STORAGE_PATH"])
        assert storage.exists(document.storage_key)
        assert document.file_url == document.storage_key
        assert not document.file_url.startswith("http")
        assert document.original_filename == "passport.pdf"
        assert document.file_type == "pdf"
        assert document.file_size == len(pdf_upload_bytes())


def test_valid_png_and_jpeg_uploads(client, app):
    login_with_pin(client, app)

    png_response = authenticated_upload(client, "image.png", image_upload_bytes("PNG"))
    jpg_response = authenticated_upload(client, "photo.jpeg", image_upload_bytes("JPEG"))

    assert png_response.status_code == 200
    assert jpg_response.status_code == 200
    with app.app_context():
        documents = Document.query.order_by(Document.id).all()
        assert [document.file_type for document in documents] == ["png", "jpg"]


def test_invalid_extension_is_rejected(client, app):
    login_with_pin(client, app)

    response = authenticated_upload(client, "notes.txt", b"plain text")

    assert response.status_code == 200
    assert "Only valid PDF" in response.get_data(as_text=True)
    with app.app_context():
        assert Document.query.count() == 0


def test_spoofed_file_content_is_rejected(client, app):
    login_with_pin(client, app)

    response = authenticated_upload(client, "fake.pdf", b"not a real pdf")

    assert response.status_code == 200
    assert "Only valid PDF" in response.get_data(as_text=True)
    with app.app_context():
        assert Document.query.count() == 0


def test_oversized_upload_is_rejected(client, app):
    login_with_pin(client, app)

    app.config["MAX_CONTENT_LENGTH"] = 32
    response = authenticated_upload(client, "large.pdf", pdf_upload_bytes() * 4)

    assert response.status_code in {200, 413}
    with app.app_context():
        assert Document.query.count() == 0


def test_private_local_download_requires_owner_and_pin(client, app):
    login_with_pin(client, app)
    authenticated_upload(client, "passport.pdf", pdf_upload_bytes())

    with app.app_context():
        document = Document.query.one()
        document_id = document.id

    response = client.get(f"/documents/download/{document_id}")

    assert response.status_code == 200
    assert response.data.startswith(b"%PDF-")
    assert "passport.pdf" in response.headers["Content-Disposition"]

    with app.app_context():
        create_user(username="bob", email="bob@example.com")

    token = get_csrf_token(client, "/dashboard")
    client.post("/logout", data={"csrf_token": token})
    login(client, identifier="bob")
    mark_pin_verified(client)

    assert client.get(f"/documents/download/{document_id}").status_code == 404


def test_delete_removes_local_file_and_database_record(client, app):
    login_with_pin(client, app)
    authenticated_upload(client, "passport.pdf", pdf_upload_bytes())

    with app.app_context():
        document = Document.query.one()
        document_id = document.id
        storage_key = document.storage_key
        storage = LocalStorage(app.config["LOCAL_STORAGE_PATH"])
        assert storage.exists(storage_key)

    token = get_csrf_token(client, "/documents")
    response = client.post(
        f"/documents/delete/{document_id}",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        assert Document.query.count() == 0
        assert not LocalStorage(app.config["LOCAL_STORAGE_PATH"]).exists(storage_key)


def test_storage_delete_failure_keeps_database_record(client, app):
    login_with_pin(client, app)
    authenticated_upload(client, "passport.pdf", pdf_upload_bytes())

    class FailingDeleteStorage(LocalStorage):
        def delete(self, storage_key):
            raise StorageError("backend unavailable")

    with app.app_context():
        document_id = Document.query.one().id
        app.extensions["malath_storage"] = FailingDeleteStorage(app.config["LOCAL_STORAGE_PATH"])

    token = get_csrf_token(client, "/documents")
    response = client.post(
        f"/documents/delete/{document_id}",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        assert Document.query.count() == 1


def test_database_failure_after_upload_cleans_up_file(client, app, monkeypatch):
    login_with_pin(client, app)
    original_commit = db.session.commit

    def fail_commit_once():
        if any(isinstance(item, Document) for item in db.session.new):
            raise SQLAlchemyError("database unavailable")
        original_commit()

    monkeypatch.setattr(db.session, "commit", fail_commit_once)

    response = authenticated_upload(client, "passport.pdf", pdf_upload_bytes())

    assert response.status_code == 200
    with app.app_context():
        assert Document.query.count() == 0
        storage = LocalStorage(app.config["LOCAL_STORAGE_PATH"])
        assert not any(storage.base_path.rglob("*.*"))
