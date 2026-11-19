from flask import Blueprint

oyu_bp = Blueprint("oyu", __name__)

from app.blueprints.oyu import routes  # noqa: E402,F401
