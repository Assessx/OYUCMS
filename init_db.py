"""Create and seed the OYUCMS SQLite database."""

import os
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.category import Category
from app.models.comment import Comment
from app.models.commerce import Coupon, GuestbookEntry, Wallet
from app.models.post import Post
from app.models.tag import Tag
from app.models.user import User

app = create_app()

USERS = [
    ("user-admin", "admin", "admin@oyucms.com", "Admin@123", "admin", "System administrator"),
    ("user-editor", "editor", "editor@oyucms.com", "Editor@123", "editor", "Content editor"),
    ("user-alice", "alice", "alice@oyucms.com", "Alice@123", "reader", "Alice"),
    ("user-bob", "bob", "bob@oyucms.com", "Bob@123", "reader", "Bob"),
    ("user-demo", "demo", "demo@oyucms.com", "Demo@123", "reader", "Demo user"),
    ("user-qa", "qa", "qa@oyucms.com", "Qa@123", "reader", "QA user"),
]

POSTS = [
    ("post-0001", "Welcome to OYUCMS", "OYUCMS is a lightweight content management system for publishing articles, categories, and pages.", "published", "user-admin", "cat-news", 120),
    ("post-0002", "Editorial workflow", "A short guide to drafting, reviewing, and publishing content in OYUCMS.", "published", "user-editor", "cat-guides", 64),
    ("post-0003", "Media library guide", "How to upload, organize, and reuse images and attachments across the site.", "published", "user-editor", "cat-guides", 31),
    ("post-draft", "Q4 content roadmap", "Draft: upcoming campaigns, editorial priorities, and publishing milestones.", "draft", "user-admin", "cat-news", 3),
]


def main():
    with app.app_context():
        db.drop_all()
        db.create_all()
        os.makedirs(os.path.join(app.instance_path, "restore"), exist_ok=True)

        for uid, username, email, password, role, bio in USERS:
            db.session.add(User(
                id=uid,
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role=role,
                is_active=True,
                is_confirmed=True,
                confirmed_at=datetime.utcnow(),
                bio=bio,
            ))

        categories = {
            "cat-news": Category(id="cat-news", name="News", slug="news", description="Product and company news", color="#ef4444"),
            "cat-guides": Category(id="cat-guides", name="Guides", slug="guides", description="How-to and documentation", color="#3b82f6"),
        }
        for c in categories.values():
            db.session.add(c)

        tags = {
            "tag-flask": Tag(id="tag-flask", name="Flask", slug="flask"),
            "tag-cms": Tag(id="tag-cms", name="CMS", slug="cms"),
        }
        for t in tags.values():
            db.session.add(t)

        db.session.flush()

        now = datetime.utcnow()
        for pid, title, body, status, author_id, cat_id, views in POSTS:
            post = Post(
                id=pid,
                title=title,
                body=body,
                excerpt=body[:160],
                status=status,
                views=views,
                author_id=author_id,
                category_id=cat_id,
                published_at=now - timedelta(days=2) if status == "published" else None,
                created_at=now - timedelta(days=3),
            )
            post.tags.append(tags["tag-flask"])
            post.tags.append(tags["tag-cms"])
            db.session.add(post)

        db.session.add_all([
            Comment(id="comment-1", body="Nice introduction to OYUCMS.", author_id="user-alice", post_id="post-0001", is_approved=True),
            Comment(id="comment-2", body="The editorial guide is useful, thanks!", author_id="user-bob", post_id="post-0002", is_approved=True),
            GuestbookEntry(author="alice", body="Looking forward to the next release."),
            GuestbookEntry(author="bob", body="The new media library works well."),
        ])

        db.session.add_all([
            Wallet(id="wallet-demo", email="demo@oyucms.com", balance=1000.0, note="Demo wallet"),
            Wallet(id="wallet-user", email="qa@oyucms.com", balance=50.0, note="QA wallet"),
        ])

        db.session.add(Coupon(code="OYU-2026", remaining=5, total=5, used=0))

        db.session.commit()

        print("[OYUCMS] database ready: instance/oyucms.db")
        for _, _, email, password, role, _ in USERS:
            print(f"  {role:<7} {email} / {password}")


if __name__ == "__main__":
    main()
