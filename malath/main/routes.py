from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from ..i18n import get_lang, get_translations
from ..models import Document, get_category_counts
from ..security import is_pin_verified
from . import bp


@bp.route("/")
def index():
    lang = get_lang()
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard", lang=lang))
    return render_template("index.html", t=get_translations(lang), lang=lang)


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
