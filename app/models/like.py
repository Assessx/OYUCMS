import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db


class Like(db.Model):
    """Like model for post reactions."""
    
    __tablename__ = 'likes'
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),
    )
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id'), nullable=False)
    post_id: Mapped[str] = mapped_column(String(36), ForeignKey('posts.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="likes")
    post: Mapped["Post"] = relationship("Post", back_populates="likes")
    
    def __repr__(self):
        return f'<Like by {self.user.username if self.user else "Unknown"} on post {self.post_id}>'
    
    def to_dict(self):
        """Convert like to dictionary for API responses."""
        return {
            'id': str(self.id),
            'user': self.user.to_dict() if self.user else None,
            'post_id': str(self.post_id),
            'created_at': self.created_at.isoformat()
        }