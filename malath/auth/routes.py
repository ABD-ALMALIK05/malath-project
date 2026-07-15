from functools import wraps

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from ..extensions import db
from ..i18n import get_lang, get_translations
from ..models import User
from ..security import (
    check_rate_limit,
    clear_pin_verification,
    is_pin_verified,
    mark_pin_verified,
    password_meets_policy,
    safe_redirect_target,
)
from . import bp


def pin_required_route(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        lang = get_lang()
        t = get_translations(lang)
        if not is_pin_verified():
            flash(t["enter_pin_first"], "warning")
            return redirect(url_for("auth.verify_pin", next=request.path, lang=lang))
        return view_func(*args, **kwargs)

    return wrapper


@bp.route("/register", methods=["GET", "POST"])
def register():
    lang = get_lang()
    t = get_translations(lang)

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard", lang=lang))

    if request.method == "POST":
        if not check_rate_limit("register", request.remote_addr or "local"):
            return rate_limited_response(t, lang)

        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        pin = request.form.get("pin", "").strip()

        if not full_name or not username or not email or not password or not pin:
            flash(t["all_fields_required"], "danger")
            return redirect(url_for("auth.register", lang=lang))

        if not pin.isdigit() or len(pin) != 6:
            flash(t["pin_required"], "danger")
            return redirect(url_for("auth.register", lang=lang))

        if not password_meets_policy(password):
            flash(t["password_policy"], "danger")
            return redirect(url_for("auth.register", lang=lang))

        if User.query.filter_by(username=username).first():
            flash(t["username_exists"], "danger")
            return redirect(url_for("auth.register", lang=lang))

        if User.query.filter_by(email=email).first():
            flash(t["email_exists"], "danger")
            return redirect(url_for("auth.register", lang=lang))

        user = User(full_name=full_name, username=username, email=email)
        user.set_password(password)
        user.set_pin(pin)

        db.session.add(user)
        db.session.commit()

        flash(t["register_success"], "success")
        return redirect(url_for("auth.login", lang=lang))

    return render_template("register.html", t=t, lang=lang)


@bp.route("/login", methods=["GET", "POST"])
def login():
    lang = get_lang()
    t = get_translations(lang)
    next_url = safe_redirect_target(request.args.get("next"), "main.dashboard", lang=lang)

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard", lang=lang))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "").strip()
        rate_key = f"{request.remote_addr or 'local'}:{identifier.lower()}"

        if not check_rate_limit("login", rate_key):
            return rate_limited_response(t, lang)

        if not identifier or not password:
            flash(t["all_fields_required"], "danger")
            return redirect(url_for("auth.login", next=next_url, lang=lang))

        user = User.query.filter(
            or_(User.email == identifier.lower(), User.username == identifier)
        ).first()

        if user and user.check_password(password):
            login_user(user)
            clear_pin_verification()
            flash(t["login_success"], "success")
            return redirect(next_url)

        flash(t["invalid_credentials"], "danger")
        return redirect(url_for("auth.login", next=next_url, lang=lang))

    return render_template("login.html", t=t, lang=lang)


@bp.route("/verify-pin", methods=["GET", "POST"])
@login_required
def verify_pin():
    lang = get_lang()
    t = get_translations(lang)
    next_url = safe_redirect_target(request.args.get("next"), "documents.documents", lang=lang)

    if request.method == "POST":
        rate_key = f"{request.remote_addr or 'local'}:{current_user.id}"
        if not check_rate_limit("pin", rate_key):
            return rate_limited_response(t, lang)

        pin = request.form.get("pin", "").strip()

        if not pin.isdigit() or len(pin) != 6:
            flash(t["pin_required"], "danger")
            return redirect(url_for("auth.verify_pin", next=next_url, lang=lang))

        if current_user.check_pin(pin):
            mark_pin_verified()
            flash(t["pin_success"], "success")
            return redirect(next_url)

        flash(t["pin_invalid"], "danger")

    return render_template("verify_pin.html", t=t, lang=lang, next_url=next_url)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    lang = get_lang()
    t = get_translations(lang)
    logout_user()
    clear_pin_verification()
    flash(t["logout_success"], "success")
    return redirect(url_for("auth.login", lang=lang))


@bp.route("/documents/clear-pin", methods=["POST"])
@login_required
def clear_pin():
    lang = get_lang()
    clear_pin_verification()
    flash(get_translations(lang)["documents_protected"], "info")
    return redirect(url_for("main.dashboard", lang=lang))


def rate_limited_response(t, lang):
    return (
        render_template(
            "error.html",
            t=t,
            lang=lang,
            status_code=429,
            message=t["too_many_attempts"],
        ),
        429,
    )
