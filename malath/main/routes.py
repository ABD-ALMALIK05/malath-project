from flask import current_app, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..i18n import get_lang, get_translations
from ..models import Document, get_category_counts
from ..security import is_pin_verified
from ..version import __version__
from . import bp


@bp.route("/")
def index():
    lang = get_lang()
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard", lang=lang))
    return render_template("index.html", t=get_translations(lang), lang=lang)


@bp.get("/health")
def health():
    response = {
        "status": "ok",
        "application": "Malath",
        "version": __version__,
    }

    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        db.session.rollback()
        current_app.logger.warning(
            "health_check_failed component=database error_type=%s",
            type(error).__name__,
        )
        response["status"] = "unavailable"
        return jsonify(response), 503

    return jsonify(response)


@bp.route("/dashboard")
@login_required
def dashboard():
    lang = get_lang()
    counts = get_category_counts(current_user.id)
    recent_documents = (
        Document.query.filter_by(user_id=current_user.id)
        .order_by(Document.upload_date.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        t=get_translations(lang),
        lang=lang,
        counts=counts,
        recent_documents=recent_documents,
        pin_verified=is_pin_verified(),
    )
