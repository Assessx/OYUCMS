from datetime import datetime, timedelta

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import desc, or_

from app.blueprints.blog import blog_bp
from app.blueprints.blog.forms import CommentForm, SearchForm
from app.extensions import db
from app.models.category import Category
from app.models.comment import Comment
from app.models.like import Like
from app.models.post import Post
from app.models.tag import Tag


@blog_bp.route("/")
def index():
    """OYUCMS homepage with paginated posts."""
    page = request.args.get("page", 1, type=int)
    posts = (
        Post.query.filter_by(status="published")
        .order_by(desc(Post.published_at))
        .paginate(page=page, per_page=10, error_out=False)
    )

    week_ago = datetime.utcnow() - timedelta(days=7)
    featured_post = (
        Post.query.filter(Post.status == "published", Post.published_at >= week_ago)
        .order_by(desc(Post.views))
        .first()
    )

    recent_posts = (
        Post.query.filter_by(status="published")
        .order_by(desc(Post.published_at))
        .limit(5)
        .all()
    )

    popular_tags = [(tag, tag.post_count) for tag in Tag.query.all()]
    popular_tags = sorted(popular_tags, key=lambda x: x[1], reverse=True)[:10]
    categories_with_counts = [(cat, cat.post_count) for cat in Category.query.all()]

    return render_template(
        "blog/index.html",
        posts=posts,
        featured_post=featured_post,
        recent_posts=recent_posts,
        popular_tags=popular_tags,
        categories=categories_with_counts,
    )


@blog_bp.route("/post/<slug>")
def post_detail(slug):
    """Individual post view."""
    post = Post.query.filter_by(slug=slug, status="published").first_or_404()

    post.views = (post.views or 0) + 1
    db.session.commit()

    comments = (
        Comment.query.filter_by(post_id=post.id, parent_id=None, is_approved=True)
        .order_by(Comment.created_at.asc())
        .all()
    )

    related_posts = (
        Post.query.filter(Post.id != post.id, Post.status == "published")
        .order_by(desc(Post.published_at))
        .limit(3)
        .all()
    )

    user_liked = False
    if current_user.is_authenticated:
        user_liked = (
            Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
            is not None
        )

    form = CommentForm()
    return render_template(
        "blog/post.html",
        post=post,
        comments=comments,
        related_posts=related_posts,
        user_liked=user_liked,
        form=form,
    )


@blog_bp.route("/post/<slug>/like", methods=["POST"])
@login_required
def toggle_like(slug):
    post = Post.query.filter_by(slug=slug, status="published").first_or_404()
    existing = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()

    if existing:
        db.session.delete(existing)
        liked = False
    else:
        db.session.add(Like(user_id=current_user.id, post_id=post.id))
        liked = True

    db.session.commit()
    return jsonify({"liked": liked, "count": Like.query.filter_by(post_id=post.id).count()})


@blog_bp.route("/post/<slug>/comment", methods=["POST"])
@login_required
def add_comment(slug):
    post = Post.query.filter_by(slug=slug, status="published").first_or_404()
    form = CommentForm()

    if form.validate_on_submit():
        comment = Comment(
            body=form.body.data,
            author_id=current_user.id,
            post_id=post.id,
            parent_id=form.parent_id.data or None,
        )
        db.session.add(comment)
        db.session.commit()
        flash("Comment posted successfully!", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")

    return redirect(url_for("blog.post_detail", slug=slug))


@blog_bp.route("/category/<slug>")
def category_posts(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    posts = (
        Post.query.filter_by(category_id=category.id, status="published")
        .order_by(desc(Post.published_at))
        .paginate(page=page, per_page=10, error_out=False)
    )
    return render_template("blog/category.html", category=category, posts=posts)


@blog_bp.route("/tag/<slug>")
def tag_posts(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    posts = (
        Post.query.filter(Post.tags.contains(tag), Post.status == "published")
        .order_by(desc(Post.published_at))
        .paginate(page=page, per_page=10, error_out=False)
    )
    return render_template("blog/tag.html", tag=tag, posts=posts)


@blog_bp.route("/search")
def search():
    """Site search."""
    form = SearchForm()
    posts = None
    search_term = request.args.get("q", "").strip()

    if search_term:
        form.q.data = search_term
        page = request.args.get("page", 1, type=int)
        posts = (
            Post.query.filter(
                Post.status == "published",
                or_(
                    Post.title.ilike(f"%{search_term}%"),
                    Post.body.ilike(f"%{search_term}%"),
                ),
            )
            .order_by(desc(Post.published_at))
            .paginate(page=page, per_page=10, error_out=False)
        )

    return render_template(
        "blog/search.html",
        form=form,
        posts=posts,
        search_term=search_term,
    )
