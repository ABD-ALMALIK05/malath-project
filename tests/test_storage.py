import io

import pytest
from sqlalchemy.exc import SQLAlchemyError

from malath.extensions import db
from malath.models import Document
from malath.services.file_validation import FileValidationError, validate_upload
from malath.services.storage import (
    LocalStorage,
    StorageConfigurationError,
    StorageError,
    get_storage,
)

from .conftest import upload_document


def test_local_storage_rejects_path_traversal(tmp_path):
    storage = LocalStorage(tmp_path)

    with pytest.raises(StorageError):
        storage.save(io.BytesIO(b"content"), "../outside.pdf", "application/pdf")

    assert not (tmp_path.parent / "outside.pdf").exists()


def test_unknown_storage_backend_fails_clearly(app):
    app.config["STORAGE_BACKEND"] = "unknown"
    app.extensions.pop("malath_storage", None)

    with pytest.raises(StorageConfigurationError, match="Unsupported storage backend"):
        get_storage()


def test_s3_backend_requires_bucket_and_region(app):
    app.config.update(STORAGE_BACKEND="s3", AWS_BUCKET_NAME=None, AWS_REGION=None)
    app.extensions.pop("malath_storage", None)

    with pytest.raises(StorageConfigurationError, match="bucket and region"):
        get_storage()


def test_valid_png_and_jpeg_uploads(pin_verified_client, valid_image_upload):
    png_content, png_name = valid_image_upload
    from .conftest import image_upload_bytes

    png_response = upload_document(pin_verified_client, png_content, png_name)
    jpeg_response = upload_document(pin_verified_client, image_upload_bytes("JPEG"), "photo.jpeg")

    assert png_response.status_code == 200
    assert jpeg_response.status_code == 200
    assert [document.file_type for document in Document.query.order_by(Document.id)] == [
        "png",
        "jpg",
    ]


def test_empty_upload_is_rejected(pin_verified_client):
    response = upload_document(pin_verified_client, b"", "empty.pdf")

    assert response.status_code == 200
    assert "selected file is empty" in response.get_data(as_text=True)


def test_mismatched_image_extension_is_rejected(valid_image_upload):
    from werkzeug.datastructures import FileStorage

    content, _ = valid_image_upload
    upload = FileStorage(stream=io.BytesIO(content), filename="image.jpg")

    with pytest.raises(FileValidationError, match="invalid_file_type"):
        validate_upload(upload, 1024)


def test_storage_delete_failure_keeps_database_record(app, pin_verified_client, valid_pdf_upload):
    content, filename = valid_pdf_upload
    upload_document(pin_verified_client, content, filename)

    class FailingDeleteStorage(LocalStorage):
        def delete(self, storage_key):
            raise StorageError("backend unavailable")

    document_id = Document.query.one().id
    app.extensions["malath_storage"] = FailingDeleteStorage(app.config["LOCAL_STORAGE_PATH"])

    from .conftest import get_csrf_token

    token = get_csrf_token(pin_verified_client, "/documents")
    response = pin_verified_client.post(
        f"/documents/delete/{document_id}",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert Document.query.count() == 1


def test_database_failure_after_upload_cleans_up_file(
    app, pin_verified_client, valid_pdf_upload, monkeypatch
):
    original_commit = db.session.commit

    def fail_document_commit():
        if any(isinstance(item, Document) for item in db.session.new):
            raise SQLAlchemyError("database unavailable")
        original_commit()

    monkeypatch.setattr(db.session, "commit", fail_document_commit)
    content, filename = valid_pdf_upload
    response = upload_document(pin_verified_client, content, filename)

    assert response.status_code == 200
    assert Document.query.count() == 0
    storage = LocalStorage(app.config["LOCAL_STORAGE_PATH"])
    assert not any(storage.base_path.rglob("*.*"))
