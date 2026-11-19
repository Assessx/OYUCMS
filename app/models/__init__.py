# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User
from app.models.category import Category
from app.models.tag import Tag
from app.models.post import Post, post_tags
from app.models.comment import Comment
from app.models.like import Like
from app.models.commerce import Wallet, Coupon, Order, GuestbookEntry, PasswordResetToken

__all__ = [
    'User',
    'Category',
    'Tag',
    'Post',
    'post_tags',
    'Comment',
    'Like',
    'Wallet',
    'Coupon',
    'Order',
    'GuestbookEntry',
    'PasswordResetToken',
]
