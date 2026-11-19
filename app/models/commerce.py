import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def _uid():
    return str(uuid.uuid4())


class Wallet(db.Model):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uid)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=1000.0, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=True)

    def to_dict(self):
        return {"id": self.id, "email": self.email, "balance": self.balance, "note": self.note}


class Coupon(db.Model):
    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self):
        return {"code": self.code, "remaining": self.remaining, "total": self.total, "used": self.used}


class Order(db.Model):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(36), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="paid")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "uid": self.uid, "amount": self.amount, "status": self.status}


class GuestbookEntry(db.Model):
    __tablename__ = "guestbook"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author: Mapped[str] = mapped_column(String(80), default="guest")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "author": self.author,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    token: Mapped[str] = mapped_column(String(16), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
