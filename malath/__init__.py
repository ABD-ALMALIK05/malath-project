from importlib import import_module
from pathlib import Path

from flask import Flask

from .config import Config
from .extensions import db, login_manager
from .i18n import get_lang, get_translations
from .security import CSRFError, generate_csrf_token, validate_csrf_token


def create_app(config_object=None):
    app = Flask(__name__)

    app.config.from_object(Config)
    if isinstance(config_object, dict):
        app.config.update(config_object)
    elif config_object is not None:
        app.config.from_object(config_object)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if app.config.get("STORAGE_BACKEND", "local") == "local":
        Path(app.config["LOCAL_STORAGE_PATH"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    import_module("malath.models")
    import_module("malath.auth.routes")
    import_module("malath.documents.routes")
    import_module("malath.main.routes")

    from .auth import bp as auth_bp
    from .documents import bp as documents_bp
    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)

    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.before_request
    def protect_state_changing_requests():
        validate_csrf_token()

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        return response

    @app.context_processor
    def inject_globals():
        return {"current_lang": get_lang()}

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        lang = get_lang()
        return (
            render_security_error(
                status_code=400,
                message=get_translations(lang)["csrf_error"],
                lang=lang,
            ),
            400,
        )

    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()
        print("Database tables initialized.")

    return app


def render_security_error(status_code, message, lang):
    from flask import render_template

    return render_template(
        "error.html",
        t=get_translations(lang),
        lang=lang,
        status_code=status_code,
        message=message,
    )
