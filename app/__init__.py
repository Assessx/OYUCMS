import os

from flask import Flask, render_template

from app.config import config
from app.extensions import init_extensions


def create_app(config_name=None):
    """Application factory for OYUCMS."""

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    init_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_context_processors(app)

    upload_dir = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    app.jinja_env.globals["OYU_VERSION"] = app.config.get("OYU_VERSION", "2.0.0")
    app.jinja_env.globals["OYU_SITE_NAME"] = app.config.get("OYU_SITE_NAME", "OYUCMS")

    return app


def register_blueprints(app):
    """Register the OYUCMS blueprints."""

    from app.blueprints.auth import auth_bp
    from app.blueprints.blog import blog_bp
    from app.blueprints.oyu import oyu_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(blog_bp)
    app.register_blueprint(oyu_bp, url_prefix="/oyu")


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def internal_error(error):
        from app.extensions import db

        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return render_template("errors/413.html"), 413


def register_context_processors(app):
    from app.context_processors import utility_processor

    app.context_processor(utility_processor)
