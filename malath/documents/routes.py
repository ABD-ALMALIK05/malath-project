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
    form_data = {"title": "", "category": "personal", "description": ""}
    field_errors = {}

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("file")
        form_data = {"title": title, "category": category, "description": description}

        if not title:
            field_errors["title"] = t["doc_title_required"]
            flash(t["doc_title_required"], "danger")
            return render_upload_form(t, lang, form_data, field_errors)

        if not file or not file.filename:
            field_errors["file"] = t["file_required"]
            flash(t["file_required"], "danger")
            return render_upload_form(t, lang, form_data, field_errors)

        try:
            validated_file = validate_upload(file, current_app.config["MAX_CONTENT_LENGTH"])
        except FileValidationError as error:
            field_errors["file"] = t[error.message_key]
            flash(t[error.message_key], "danger")
            return render_upload_form(t, lang, form_data, field_errors)

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
        except StorageError as error:
            current_app.logger.warning("document_upload_failed error_type=%s", type(error).__name__)
            flash(t["storage_upload_failed"], "danger")
            return render_upload_form(t, lang, form_data, field_errors)

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
        except SQLAlchemyError as error:
            db.session.rollback()
            current_app.logger.warning(
                "document_database_save_failed error_type=%s", type(error).__name__
            )
            try:
                delete_object(storage_key)
            except StorageError as cleanup_error:
                current_app.logger.warning(
                    "uploaded_object_cleanup_failed error_type=%s",
                    type(cleanup_error).__name__,
                )
            flash(t["storage_upload_failed"], "danger")
            return render_upload_form(t, lang, form_data, field_errors)

        flash(t["document_uploaded"], "success")
        return redirect(url_for("documents.documents", lang=lang))

    return render_upload_form(t, lang, form_data, field_errors)


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
    except StorageError as error:
        current_app.logger.warning("document_download_failed error_type=%s", type(error).__name__)
        flash(t["storage_download_failed"], "danger")
        return redirect(url_for("documents.documents", lang=lang))


@bp.route("/documents/edit/<int:document_id>", methods=["GET", "POST"])
@login_required
@pin_required_route
def edit_document(document_id):
    lang = get_lang()
    t = get_translations(lang)
    document = get_owned_document_or_404(document_id)
    form_data = {
        "title": document.title,
        "category": document.category,
        "description": document.description or "",
    }
    field_errors = {}

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        form_data = {"title": title, "category": category, "description": description}

        if not title:
            field_errors["title"] = t["doc_title_required"]
            flash(t["doc_title_required"], "danger")
            return render_edit_form(t, lang, document, form_data, field_errors)

        document.title = title
        document.category = category
        document.description = description

        db.session.commit()
        flash(t["document_updated"], "success")
        return redirect(url_for("documents.documents", lang=lang))

    return render_edit_form(t, lang, document, form_data, field_errors)


@bp.route("/documents/delete/<int:document_id>", methods=["POST"])
@login_required
@pin_required_route
def delete_document(document_id):
    lang = get_lang()
    t = get_translations(lang)
    document = get_owned_document_or_404(document_id)

    try:
        delete_object(document.storage_key)
    except StorageError as error:
        current_app.logger.warning(
            "document_storage_delete_failed error_type=%s", type(error).__name__
        )
        flash(t["storage_delete_failed"], "danger")
        return redirect(url_for("documents.documents", lang=lang))

    db.session.delete(document)
    try:
        db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.warning(
            "document_database_delete_failed error_type=%s", type(error).__name__
        )
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


def render_upload_form(t, lang, form_data, field_errors):
    return render_template(
        "upload.html",
        t=t,
        lang=lang,
        form_data=form_data,
        field_errors=field_errors,
    )


def render_edit_form(t, lang, document, form_data, field_errors):
    return render_template(
        "edit_document.html",
        t=t,
        lang=lang,
        document=document,
        form_data=form_data,
        field_errors=field_errors,
    )
