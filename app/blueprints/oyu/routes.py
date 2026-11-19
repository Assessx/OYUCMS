"""OYUCMS API and administration module."""

import base64
import io
import json
import os
import pickle
import platform
import secrets
import subprocess
import time
import urllib.request
import zipfile
from datetime import datetime

import jwt as pyjwt
import yaml
from flask import (
    current_app,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    send_file,
)
from flask_login import current_user
from lxml import etree
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from app.blueprints.oyu import oyu_bp
from app.extensions import db
from app.models.commerce import Coupon, GuestbookEntry, Order, PasswordResetToken, Wallet
from app.models.post import Post
from app.models.user import User

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
UPLOAD_DIR = os.path.join(BASE_DIR, "app", "static", "uploads")
RESTORE_DIR = os.path.join(BASE_DIR, "instance", "restore")
JWT_SECRET = "oyu-jwt-secret-2024"


def _b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _issue_token(user, algorithm="HS256", secret=JWT_SECRET):
    payload = {
        "uid": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "iat": int(time.time()),
    }
    if algorithm.lower() == "none":
        return pyjwt.encode(payload, None, algorithm="none")
    return pyjwt.encode(payload, secret, algorithm=algorithm)


def _current_uid_from_token():
    token = request.headers.get("Authorization", "")
    if token.lower().startswith("bearer "):
        token = token[7:]
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def _json_body():
    return request.get_json(silent=True) or request.form.to_dict() or {}


def _resolve_path(path: str) -> str:
    if not path:
        return BASE_DIR
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(BASE_DIR, path))


def _rows(rows):
    result = []
    for row in rows:
        item = {}
        for key, value in row._mapping.items():
            item[str(key)] = value if isinstance(value, (int, float, type(None))) else str(value)
        result.append(item)
    return result


@oyu_bp.route("/")
def dashboard():
    stats = {
        "posts": Post.query.count(),
        "users": User.query.count(),
        "comments": GuestbookEntry.query.count(),
        "orders": Order.query.count(),
        "coupons": Coupon.query.count(),
    }
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(5).all()
    return render_template("oyu/dashboard.html", stats=stats, recent_posts=recent_posts)


@oyu_bp.route("/health")
def health():
    return jsonify({"ok": True, "app": "OYUCMS", "version": current_app.config["OYU_VERSION"]})


@oyu_bp.route("/comments")
def comments_page():
    comments = GuestbookEntry.query.order_by(GuestbookEntry.id.desc()).all()
    return render_template("oyu/comments.html", comments=comments)


@oyu_bp.route("/search")
def search_page():
    q = request.args.get("q", "")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Search - OYUCMS</title>
<style>body{{font-family:Arial;margin:40px}}code{{background:#eee;padding:2px 4px}}</style></head>
<body><h1>Search</h1><p>Query: {q}</p>
<p>No matching content. <a href="/oyu/">Back to dashboard</a></p></body></html>"""
    return html


@oyu_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    data = _json_body()
    email = str(data.get("email", ""))
    password = str(data.get("password", ""))

    user = User.query.filter_by(email=email.lower()).first()
    if user and check_password_hash(user.password_hash, password):
        return jsonify({"ok": True, "token": _issue_token(user),
                        "user": {"id": user.id, "email": user.email, "role": user.role}})

    raw = (
        "SELECT id, email, username, role FROM users "
        f"WHERE email = '{email}' AND password_hash = '{password}' LIMIT 1"
    )
    try:
        row = db.session.execute(text(raw)).fetchone()
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    if not row:
        return jsonify({"ok": False, "error": "invalid credentials"}), 401
    user = db.session.get(User, row[0])
    return jsonify({"ok": True, "token": _issue_token(user),
                    "user": {"id": user.id, "email": user.email, "role": user.role}})


@oyu_bp.route("/api/auth/token", methods=["POST"])
def issue_token():
    data = _json_body()
    user = User.query.filter_by(email=str(data.get("email", "")).lower()).first()
    if not user or not check_password_hash(user.password_hash, str(data.get("password", ""))):
        return jsonify({"ok": False, "error": "invalid credentials"}), 401
    return jsonify({"ok": True, "token": _issue_token(user), "role": user.role})


@oyu_bp.route("/api/auth/reset/request", methods=["POST"])
def api_reset_request():
    email = str(_json_body().get("email", "")).lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"ok": False, "error": "account not found"}), 404
    token = secrets.token_hex(3)
    db.session.add(PasswordResetToken(email=email, token=token))
    db.session.commit()
    return jsonify({"ok": True, "email": email, "resetToken": token})


@oyu_bp.route("/api/auth/reset/confirm", methods=["POST"])
def api_reset_confirm():
    data = _json_body()
    email = str(data.get("email", "")).lower()
    token = str(data.get("token", ""))
    new_password = str(data.get("newPassword", ""))
    row = PasswordResetToken.query.filter_by(email=email, token=token, used=False).first()
    if not row:
        return jsonify({"ok": False, "error": "invalid token"}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"ok": False, "error": "account not found"}), 404
    user.password_hash = generate_password_hash(new_password)
    row.used = True
    db.session.commit()
    return jsonify({"ok": True, "email": email})


@oyu_bp.route("/api/search")
def api_search():
    q = request.args.get("q", "")
    raw = (
        "SELECT id, title, slug, status, author_id FROM posts "
        f"WHERE title LIKE '%{q}%' LIMIT 50"
    )
    try:
        rows = db.session.execute(text(raw)).fetchall()
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "rows": _rows(rows)})


@oyu_bp.route("/api/posts")
def api_posts():
    sort = request.args.get("sort", "created_at DESC")
    raw = f"SELECT id, title, status, views FROM posts ORDER BY {sort} LIMIT 20"
    try:
        rows = db.session.execute(text(raw)).fetchall()
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    return jsonify({"ok": True, "rows": _rows(rows)})


@oyu_bp.route("/api/post/<post_id>")
def api_post_detail(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({
        "ok": True,
        "post": {
            "id": post.id,
            "title": post.title,
            "slug": post.slug,
            "status": post.status,
            "body": post.body,
            "author_id": post.author_id,
            "published_at": post.published_at.isoformat() if post.published_at else None,
        },
    })


@oyu_bp.route("/api/post/<post_id>/edit", methods=["POST"])
def api_post_update(post_id):
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"ok": False, "error": "not found"}), 404
    data = _json_body()
    for field in ("title", "body", "excerpt", "status"):
        if field in data:
            setattr(post, field, data[field])
    db.session.commit()
    return jsonify({"ok": True, "post_id": post.id, "title": post.title, "status": post.status})


@oyu_bp.route("/api/user/<uid>")
def api_user_detail(uid):
    user = db.session.get(User, uid)
    if not user:
        return jsonify({"ok": False, "error": "not found"}), 404
    data = user.to_dict(include_email=True)
    data["password_hash"] = user.password_hash
    data["is_confirmed"] = user.is_confirmed
    return jsonify({"ok": True, "user": data})


@oyu_bp.route("/api/user/profile", methods=["POST"])
def api_profile_update():
    data = _json_body()
    uid = data.get("uid") or data.get("id")
    user = db.session.get(User, uid) if uid else None
    if not user:
        return jsonify({"ok": False, "error": "user not found"}), 404

    for field in ("username", "email", "bio", "avatar_url", "role", "is_active"):
        if field in data:
            value = data[field]
            if field == "is_active":
                value = bool(value)
            setattr(user, field, value)
    db.session.commit()
    return jsonify({"ok": True, "user": user.to_dict(include_email=True)})


@oyu_bp.route("/api/admin/panel")
def api_admin_panel():
    payload = _current_uid_from_token()
    if not payload:
        return jsonify({"ok": False, "error": "missing or invalid token"}), 401
    if payload.get("role") != "admin":
        return jsonify({"ok": False, "error": "admin role required", "claims": payload}), 403
    return jsonify({
        "ok": True,
        "claims": payload,
        "users": [u.to_dict(include_email=True) for u in User.query.all()],
    })


@oyu_bp.route("/api/admin/panel/legacy")
def api_admin_panel_legacy():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    parts = token.split(".")
    if len(parts) != 3:
        return jsonify({"ok": False, "error": "malformed token"}), 401
    try:
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
    except Exception:
        return jsonify({"ok": False, "error": "decode failed"}), 401
    if str(header.get("alg", "")).lower() != "none":
        return jsonify({"ok": False, "error": "unsupported token"}), 403
    if payload.get("role") != "admin":
        return jsonify({"ok": False, "error": "admin role required"}), 403
    return jsonify({"ok": True, "claims": payload,
                    "users": [u.to_dict(include_email=True) for u in User.query.all()]})


@oyu_bp.route("/api/comments", methods=["POST"])
def api_comment_create():
    data = _json_body()
    body = str(data.get("body", ""))
    if not body:
        return jsonify({"ok": False, "error": "body required"}), 400
    comment = GuestbookEntry(author=str(data.get("author", "guest")), body=body)
    db.session.add(comment)
    db.session.commit()
    return jsonify({"ok": True, "id": comment.id, "view": "/oyu/comments"})


@oyu_bp.route("/api/comments/list")
def api_comments_list():
    return jsonify({"ok": True, "comments": [c.to_dict() for c in GuestbookEntry.query.all()]})


@oyu_bp.route("/api/template/preview", methods=["POST"])
def api_template_preview():
    tpl = str(_json_body().get("tpl", _json_body().get("template", "")))
    try:
        return render_template_string("OYUCMS mail preview: " + tpl)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@oyu_bp.route("/api/cache/import", methods=["POST"])
def api_cache_import():
    payload = str(_json_body().get("payload", ""))
    try:
        raw = base64.b64decode(payload)
        obj = pickle.loads(raw)
        return jsonify({"ok": True, "type": type(obj).__name__, "repr": repr(obj)[:1000]})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@oyu_bp.route("/api/config/import", methods=["POST"])
def api_config_import():
    raw = request.get_data(as_text=True)
    if request.is_json:
        raw = str((request.get_json(silent=True) or {}).get("yaml", ""))
    try:
        obj = yaml.unsafe_load(raw)
        return jsonify({"ok": True, "type": type(obj).__name__, "repr": repr(obj)[:1000]})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@oyu_bp.route("/api/feed/import", methods=["POST"])
def api_feed_import():
    raw = request.get_data()
    if request.is_json:
        raw = str((request.get_json(silent=True) or {}).get("xml", "")).encode()
    parser = etree.XMLParser(resolve_entities=True, no_network=False, load_dtd=True, huge_tree=True)
    try:
        root = etree.fromstring(raw, parser=parser)
        return jsonify({"ok": True, "text": "".join(root.itertext())[:8000]})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@oyu_bp.route("/api/link/check")
def api_link_check():
    url = request.args.get("url", "")
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            body = resp.read(8192)
        return jsonify({"ok": True, "url": url, "status": getattr(resp, "status", None),
                        "body": body.decode("utf-8", errors="replace")})
    except Exception as exc:
        return jsonify({"ok": False, "url": url, "error": str(exc)}), 500


@oyu_bp.route("/api/system/ping")
def api_system_ping():
    host = request.args.get("host", "127.0.0.1")
    if platform.system().lower().startswith("win"):
        command = f"ping -n 1 {host}"
    else:
        command = f"ping -c 1 {host}"
    try:
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        return jsonify({"ok": True, "command": command,
                        "stdout": proc.stdout, "stderr": proc.stderr,
                        "returncode": proc.returncode})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@oyu_bp.route("/api/attachment/preview")
def api_attachment_preview():
    name = request.args.get("name", "")
    path = _resolve_path(name)
    try:
        with open(path, "rb") as fh:
            data = fh.read(65536)
        return jsonify({"ok": True, "path": path, "content": data.decode("utf-8", errors="replace")})
    except Exception as exc:
        return jsonify({"ok": False, "path": path, "error": str(exc)}), 500


@oyu_bp.route("/api/attachment/download")
def api_attachment_download():
    path = _resolve_path(request.args.get("path", ""))
    try:
        return send_file(path, as_attachment=True)
    except Exception as exc:
        return jsonify({"ok": False, "path": path, "error": str(exc)}), 500


@oyu_bp.route("/api/attachment/remove", methods=["POST"])
def api_attachment_remove():
    path = _resolve_path(request.args.get("path", ""))
    try:
        os.remove(path)
        return jsonify({"ok": True, "deleted": path})
    except Exception as exc:
        return jsonify({"ok": False, "path": path, "error": str(exc)}), 500


@oyu_bp.route("/api/media/upload", methods=["POST"])
def api_media_upload():
    fh = request.files.get("file")
    if not fh or not fh.filename:
        return jsonify({"ok": False, "error": "file field required"}), 400
    name = fh.filename
    target = os.path.join(UPLOAD_DIR, name)
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        fh.save(target)
        url = "/static/uploads/" + name.replace("\\", "/")
        return jsonify({"ok": True, "saved": target, "url": url})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@oyu_bp.route("/go")
def go():
    return redirect(request.args.get("to", "/oyu/"))


@oyu_bp.route("/api/admin/user/remove")
def api_admin_user_remove():
    if not current_user.is_authenticated or not current_user.is_admin:
        return jsonify({"ok": False, "error": "admin session required"}), 403
    uid = request.args.get("id", "")
    user = db.session.get(User, uid)
    if not user:
        return jsonify({"ok": False, "error": "user not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"ok": True, "deleted": uid})


@oyu_bp.route("/api/coupon/use", methods=["POST"])
def api_coupon_use():
    code = str(_json_body().get("code", ""))
    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon:
        return jsonify({"ok": False, "error": "coupon not found"}), 404
    if coupon.remaining <= 0:
        return jsonify({"ok": False, "error": "sold out", "remaining": coupon.remaining}), 409

    time.sleep(0.25)
    coupon.remaining -= 1
    coupon.used += 1
    db.session.commit()
    return jsonify({"ok": True, "code": code, "remaining": coupon.remaining, "used": coupon.used})


@oyu_bp.route("/api/order/settle", methods=["POST"])
def api_order_settle():
    data = _json_body()
    uid = str(data.get("uid", "wallet-demo"))
    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "amount must be numeric"}), 400
    account = db.session.get(Wallet, uid)
    if not account:
        return jsonify({"ok": False, "error": "account not found"}), 404
    account.balance = round(account.balance - amount, 2)
    db.session.add(Order(uid=account.id, amount=amount, status="paid"))
    db.session.commit()
    return jsonify({"ok": True, "uid": account.id, "charged": amount, "balance": account.balance})


@oyu_bp.route("/api/account/<uid>")
def api_account(uid):
    account = db.session.get(Wallet, uid)
    if not account:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "account": account.to_dict()})


@oyu_bp.route("/api/backup/import", methods=["POST"])
def api_backup_import():
    raw = request.get_data()
    if not raw:
        return jsonify({"ok": False, "error": "zip body required"}), 400
    os.makedirs(RESTORE_DIR, exist_ok=True)
    extracted = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for member in zf.namelist():
                target = os.path.join(RESTORE_DIR, member)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as fh:
                    fh.write(zf.read(member))
                extracted.append(os.path.abspath(target))
        return jsonify({"ok": True, "extracted": extracted})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@oyu_bp.route("/api/system/info")
def api_system_info():
    info = {}
    for key, value in current_app.config.items():
        if isinstance(value, (str, int, float, bool, type(None))):
            info[key] = value
        else:
            info[key] = str(value)
    info["MAIL_PASSWORD"] = current_app.config["MAIL_PASSWORD"]
    info["OSS_ACCESS_KEY_SECRET"] = current_app.config["OSS_ACCESS_KEY_SECRET"]
    return jsonify({"ok": True, "config": info,
                    "env": {k: v for k, v in os.environ.items() if k.startswith("OYU_")}})
