from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager


# OYUCMS extensions
db = SQLAlchemy()
login_manager = LoginManager()


def init_extensions(app):
    """Initialize the extension set used by OYUCMS."""

    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    """Load a user by ID for Flask-Login."""
    from app.models.user import User

    return db.session.get(User, user_id)
