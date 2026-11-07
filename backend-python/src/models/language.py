from datetime import date, datetime
from typing import Optional, Any
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class LanguageProfile(Base):
    __tablename__ = "language_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_language: Mapped[str] = mapped_column(String(50), default="Inglês")
    learning_focus: Mapped[str] = mapped_column(String(100), default="business")
    cefr_level: Mapped[str] = mapped_column(String(10), default="UNSET")
    study_days: Mapped[Optional[list[int]]] = mapped_column(JSON, default=[1, 2, 3, 4, 5])
    preferred_time: Mapped[str] = mapped_column(String(10), default="07:30")
    daily_duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    calendar_sync_ids: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    weaknesses_diagnosis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="language_profile")
    daily_sessions = relationship("LanguageDailySession", back_populates="language_profile", cascade="all, delete-orphan")
    vault_items = relationship("LanguageVocabularyVault", back_populates="language_profile", cascade="all, delete-orphan")


class LanguageDailySession(Base):
    __tablename__ = "language_daily_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    language_profile_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("language_profiles.id", ondelete="CASCADE"), nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ready") # ready, completed, missed
    lesson_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    user_answers: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_feedback: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    language_profile = relationship("LanguageProfile", back_populates="daily_sessions")


class LanguageVocabularyVault(Base):
    __tablename__ = "language_vocabulary_vault"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    language_profile_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("language_profiles.id", ondelete="CASCADE"), nullable=False)
    term_or_phrase: Mapped[str] = mapped_column(String(255), nullable=False)
    translation: Mapped[str] = mapped_column(String(255), nullable=False)
    context_example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mastery_level: Mapped[int] = mapped_column(SmallInteger, default=1)
    next_review_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    language_profile = relationship("LanguageProfile", back_populates="vault_items")

