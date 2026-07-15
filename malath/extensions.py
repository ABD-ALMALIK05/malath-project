from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate(compare_type=True, render_as_batch=True)

login_manager = LoginManager()
login_manager.login_view = "auth.login"
