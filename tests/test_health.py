from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError

from malath import create_app
from malath.extensions import db
from malath.models import User


def test_health_endpoint_reports_application_version(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "application": "Malath",
        "status": "ok",
        "version": "0.2.0",
    }


def test_health_endpoint_reports_database_failure(app, client, monkeypatch):
    def fail_database_check(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, RuntimeError("database unavailable"))

    monkeypatch.setattr(db.session, "execute", fail_database_check)
    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {
        "application": "Malath",
        "status": "unavailable",
        "version": "0.2.0",
    }


def test_error_pages_are_bilingual(client):
    english = client.get("/missing?lang=en")
    arabic = client.get("/missing?lang=ar")

    assert english.status_code == 404
    assert "The page you requested could not be found." in english.get_data(as_text=True)
    assert arabic.status_code == 404
    assert 'lang="ar"' in arabic.get_data(as_text=True)
    assert 'dir="rtl"' in arabic.get_data(as_text=True)
    assert "تعذر العثور على الصفحة المطلوبة." in arabic.get_data(as_text=True)


def test_internal_error_hides_exception_details(app, client):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/test-error")
    def test_error():
        raise RuntimeError("private internal detail")

    response = client.get("/test-error?lang=en")
    body = response.get_data(as_text=True)

    assert response.status_code == 500
    assert "An unexpected error occurred." in body
    assert "private internal detail" not in body


def test_initial_migration_upgrades_fresh_database(tmp_path):
    app = create_migration_app(tmp_path, "fresh.db")

    result = app.test_cli_runner().invoke(args=["db", "upgrade"])

    assert result.exit_code == 0, result.output
    with app.app_context():
        assert {"alembic_version", "document", "user"}.issubset(
            inspect(db.engine).get_table_names()
        )


def test_initial_migration_preserves_existing_data(tmp_path):
    app = create_migration_app(tmp_path, "existing.db")
    with app.app_context():
        db.create_all()
        user = User(full_name="Existing User", username="existing", email="existing@example.com")
        user.set_password("Password1")
        user.set_pin("123456")
        db.session.add(user)
        db.session.commit()

    result = app.test_cli_runner().invoke(args=["db", "upgrade"])

    assert result.exit_code == 0, result.output
    with app.app_context():
        assert User.query.filter_by(username="existing").one().email == "existing@example.com"
        assert "alembic_version" in inspect(db.engine).get_table_names()


def create_migration_app(tmp_path, database_name):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "migration-test-secret",
            "CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / database_name).as_posix()}",
            "STORAGE_BACKEND": "local",
            "LOCAL_STORAGE_PATH": str(tmp_path / "uploads"),
        }
    )
