from flask import current_app, render_template, request

from .extensions import db
from .i18n import get_lang, get_translations

ERROR_MESSAGE_KEYS = {
    400: "error_400",
    403: "error_403",
    404: "error_404",
    413: "error_413",
    429: "error_429",
    500: "error_500",
}


def render_error(status_code, message=None):
    lang = get_lang()
    translations = get_translations(lang)
    return render_template(
        "error.html",
        t=translations,
        lang=lang,
        status_code=status_code,
        message=message or translations[ERROR_MESSAGE_KEYS[status_code]],
    )


def register_error_handlers(app):
    def handle_http_error(error):
        return render_error(error.code), error.code

    for status_code in (400, 403, 404, 413, 429):
        app.register_error_handler(status_code, handle_http_error)

    @app.errorhandler(500)
    def handle_internal_error(error):
        db.session.rollback()
        original_error = getattr(error, "original_exception", None) or error
        current_app.logger.error(
            "unhandled_error endpoint=%s error_type=%s",
            request.endpoint or "unknown",
            type(original_error).__name__,
        )
        return render_error(500), 500
