from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False) # gemini, google, apple_caldav, shortcuts
    label: Mapped[str] = mapped_column(String(255), default="default")
    status: Mapped[str] = mapped_column(String(24), default="connected")
    credentials: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Criptografado com Laravel AES-256
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    scopes: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    token_prefix: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    webhook_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="integrations")

