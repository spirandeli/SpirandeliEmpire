from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    locale: Mapped[str] = mapped_column(String(8), default="pt_BR")
    agent_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ai_active: Mapped[bool] = mapped_column(Boolean, default=True)
    monthly_token_limit: Mapped[int] = mapped_column(BigInteger, default=2000000)
    tokens_used_this_month: Mapped[int] = mapped_column(BigInteger, default=0)
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    remember_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    calendar_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relacionamentos
    businesses = relationship("Business", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    approvals = relationship("ApprovalQueue", back_populates="user", cascade="all, delete-orphan")
    integrations = relationship("UserIntegration", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("AgentConversation", back_populates="user", cascade="all, delete-orphan")
    language_profile = relationship("LanguageProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class PersonalAccessToken(Base):
    __tablename__ = "personal_access_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tokenable_type: Mapped[str] = mapped_column(String(255), default="App\\Models\\User")
    tokenable_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    abilities: Mapped[Optional[str]] = mapped_column(String(500), default='["*"]')
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

