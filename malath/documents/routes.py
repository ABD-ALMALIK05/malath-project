import os
import uuid

from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..auth.routes import pin_required_route
from ..extensions import db
from ..i18n import get_lang, get_translations
from ..models import Document, get_category_counts
from ..services.file_validation import allowed_file
from ..services.storage import (
    StorageError,
    build_public_file_url,
    create_presigned_download_url,
    delete_object,
    upload_fileobj,
)
from . import bp


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

        if not allowed_file(file.filename):
            flash(t["invalid_file_type"], "danger")
            return redirect(url_for("documents.upload", lang=lang))

        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit(".", 1)[1].lower()
        stored_filename = f"users/{current_user.id}/{category}/{uuid.uuid4().hex}.{extension}"

        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)

        try:
            upload_fileobj(
                file.stream,
                stored_filename,
                file.content_type or "application/octet-stream",
            )
        except StorageError:
            current_app.logger.warning("Document upload failed", exc_info=True)
            flash(t["storage_upload_failed"], "danger")
            return redirect(url_for("documents.upload", lang=lang))

        document = Document(
            title=title,
            category=category,
            description=description,
            file_url=build_public_file_url(stored_filename),
            stored_filename=stored_filename,
            original_filename=original_filename,
            file_type=extension,
            file_size=file_size,
            user_id=current_user.id,
        )

        db.session.add(document)
        db.session.commit()

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

    if selected_category in ["government", "medical", "property", "personal"]:
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
        return redirect(create_presigned_download_url(document.stored_filename))
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
        delete_object(document.stored_filename)
    except StorageError:
        current_app.logger.warning("Document deletion failed", exc_info=True)
        flash(t["storage_delete_failed"], "danger")
        return redirect(url_for("documents.documents", lang=lang))

    db.session.delete(document)
    db.session.commit()

    flash(t["document_deleted"], "success")
    return redirect(url_for("documents.documents", lang=lang))


def get_owned_document_or_404(document_id):
    return Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
