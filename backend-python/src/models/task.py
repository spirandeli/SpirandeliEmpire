from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    BigInteger,
    Boolean,
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


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assignee: Mapped[str] = mapped_column(String(16), default="user") # 'agent' ou 'user'
    status: Mapped[str] = mapped_column(String(32), default="backlog") # backlog, ready, in_progress, supervision, done, blocked
    priority: Mapped[str] = mapped_column(String(16), default="medium") # low, medium, high, urgent
    source: Mapped[str] = mapped_column(String(16), default="user") # user, agent, webhook, automation
    position: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    agent_action: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(SmallInteger, default=0)
    status_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_calendar_provider: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    external_calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="tasks")
    business = relationship("Business", back_populates="tasks")
    approval_items = relationship("ApprovalQueue", back_populates="task")

