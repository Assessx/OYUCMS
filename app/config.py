import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


class Config:
    """OYUCMS base configuration."""

    SECRET_KEY = os.environ.get("OYU_SECRET_KEY") or "oyu-secret-key-2024"

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(INSTANCE_DIR, "oyucms.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 30}}

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH") or 16 * 1024 * 1024)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or "app/static/uploads"
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

    JWT_SECRET_KEY = os.environ.get("OYU_JWT_SECRET") or "oyu-jwt-secret-2024"
    JWT_ALGORITHM = "HS256"

    POSTS_PER_PAGE = 10
    COMMENTS_PER_PAGE = 20

    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)

    OYU_VERSION = "2.0.0"
    OYU_SITE_NAME = "OYUCMS"

    MAIL_PASSWORD = "Mail@Oyu2024"
    OSS_ACCESS_KEY_ID = "LTAI5tOYU9demoKey0001"
    OSS_ACCESS_KEY_SECRET = "oyu-demo-secret-do-not-use"


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
