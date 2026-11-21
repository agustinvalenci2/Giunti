import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow():
    # SQLite stores naive timestamps; every timestamp in this application is UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True)
    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    user: Mapped[User] = relationship(lazy="joined")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    storage_path: Mapped[str] = mapped_column(String(512))
    original_name: Mapped[str] = mapped_column(String(255))
    extension: Mapped[str] = mapped_column(String(8))
    size: Mapped[int] = mapped_column(Integer)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserDocument(Base):
    __tablename__ = "user_documents"
    __table_args__ = (UniqueConstraint("user_id", "sha256", name="unique_user_document_hash"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="uploaded")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(String(100), default="")
    prompt_version: Mapped[str] = mapped_column(String(30), default="")
    attempt_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    document: Mapped[Document] = relationship(lazy="joined")
