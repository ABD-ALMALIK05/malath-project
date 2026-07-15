from importlib import import_module
from pathlib import Path

from flask import Flask

from .config import Config
from .extensions import db, login_manager
from .i18n import get_lang


def create_app(config_object=None):
    app = Flask(__name__)

    app.config.from_object(Config)
    if isinstance(config_object, dict):
        app.config.update(config_object)
    elif config_object is not None:
        app.config.from_object(config_object)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

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

    @app.context_processor
    def inject_globals():
        return {"current_lang": get_lang()}

    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()
        print("Database tables initialized.")

    return app
