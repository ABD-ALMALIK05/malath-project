import uuid

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from ..auth.routes import pin_required_route
from ..extensions import db
from ..i18n import get_lang, get_translations
from ..models import Document, get_category_counts
from ..services.file_validation import FileValidationError, validate_upload
from ..services.storage import (
    StorageError,
    create_download_response,
    delete_object,
    save_fileobj,
)
from . import bp

DOCUMENT_CATEGORIES = {"government", "medical", "property", "personal"}


@bp.route("/upload", methods=["GET", "POST"])
@login_required
@pin_required_route
def upload():
    lang = get_lang()
    t = get_translations(lang)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("file")

        if not title:
            flash(t["doc_title_required"], "danger")
            return redirect(url_for("documents.upload", lang=lang))

        if not file or not file.filename:
            flash(t["file_required"], "danger")
            return redirect(url_for("documents.upload", lang=lang))

        try:
            validated_file = validate_upload(file, current_app.config["MAX_CONTENT_LENGTH"])
        except FileValidationError as error:
            flash(t[error.message_key], "danger")
            return redirect(url_for("documents.upload", lang=lang))

        original_filename = secure_filename(file.filename)
        if not original_filename:
            original_filename = f"document.{validated_file.extension}"
        storage_key = generate_storage_key(current_user.id, category, validated_file.extension)

        try:
            save_fileobj(
                file.stream,
                storage_key,
                validated_file.content_type,
            )
        except StorageError:
            current_app.logger.warning("Document upload failed", exc_info=True)
            flash(t["storage_upload_failed"], "danger")
            return redirect(url_for("documents.upload", lang=lang))

        document = Document(
            title=title,
            category=category,
            description=description,
            file_url=storage_key,
            stored_filename=storage_key,
            original_filename=original_filename,
            file_type=validated_file.extension,
            file_size=validated_file.size,
            user_id=current_user.id,
        )

        db.session.add(document)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.warning("Document database save failed", exc_info=True)
            try:
                delete_object(storage_key)
            except StorageError:
                current_app.logger.warning("Uploaded object cleanup failed", exc_info=True)
            flash(t["storage_upload_failed"], "danger")
            return redirect(url_for("documents.upload", lang=lang))

        flash(t["document_uploaded"], "success")
        return redirect(url_for("documents.documents", lang=lang))

    return render_template("upload.html", t=t, lang=lang)


@bp.route("/documents")
@login_required
@pin_required_route
def documents():
    lang = get_lang()
    selected_category = request.args.get("category", "").strip()
    query = Document.query.filter_by(user_id=current_user.id)

    if selected_category in DOCUMENT_CATEGORIES:
        query = query.filter_by(category=selected_category)

    documents_list = query.order_by(Document.upload_date.desc()).all()
    counts = get_category_counts(current_user.id)

    return render_template(
        "documents.html",
        t=get_translations(lang),
        lang=lang,
        documents=documents_list,
        counts=counts,
        selected_category=selected_category,
    )


@bp.route("/documents/download/<int:document_id>")
@login_required
@pin_required_route
def download_document(document_id):
    lang = get_lang()
    t = get_translations(lang)
    document = get_owned_document_or_404(document_id)

    try:
        return create_download_response(
            document.storage_key,
            document.original_filename,
            content_type_for(document.file_type),
        )
    except StorageError:
        current_app.logger.warning("Document download link generation failed", exc_info=True)
        flash(t["storage_download_failed"], "danger")
        return redirect(url_for("documents.documents", lang=lang))


@bp.route("/documents/edit/<int:document_id>", methods=["GET", "POST"])
@login_required
@pin_required_route
def edit_document(document_id):
    lang = get_lang()
    t = get_translations(lang)
    document = get_owned_document_or_404(document_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        if not title:
            flash(t["doc_title_required"], "danger")
            return redirect(url_for("documents.edit_document", document_id=document.id, lang=lang))

        document.title = title
        document.category = category
        document.description = description

        db.session.commit()
        flash(t["document_updated"], "success")
        return redirect(url_for("documents.documents", lang=lang))

    return render_template("edit_document.html", t=t, lang=lang, document=document)


@bp.route("/documents/delete/<int:document_id>", methods=["POST"])
@login_required
@pin_required_route
def delete_document(document_id):
    lang = get_lang()
    t = get_translations(lang)
    document = get_owned_document_or_404(document_id)

    try:
        delete_object(document.storage_key)
    except StorageError:
        current_app.logger.warning("Document deletion failed", exc_info=True)
        flash(t["storage_delete_failed"], "danger")
        return redirect(url_for("documents.documents", lang=lang))

    db.session.delete(document)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.warning("Document database deletion failed", exc_info=True)
        flash(t["storage_delete_failed"], "danger")
        return redirect(url_for("documents.documents", lang=lang))

    flash(t["document_deleted"], "success")
    return redirect(url_for("documents.documents", lang=lang))


def get_owned_document_or_404(document_id):
    return Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()


def generate_storage_key(user_id, category, extension):
    safe_category = category if category in DOCUMENT_CATEGORIES else "uncategorized"
    return f"users/{user_id}/{safe_category}/{uuid.uuid4().hex}.{extension}"


def content_type_for(file_type):
    if file_type == "pdf":
        return "application/pdf"
    if file_type == "png":
        return "image/png"
    return "image/jpeg"
