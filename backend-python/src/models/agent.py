from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    business_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    context_type: Mapped[str] = mapped_column(String(24), default="incubator") # incubator, operation, advisor
    status: Mapped[str] = mapped_column(String(16), default="active")
    model: Mapped[str] = mapped_column(String(64), default="gemini-3.8")
    context: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    completion_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("AgentMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="AgentMessage.id")


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_conversation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False) # user, assistant, tool, system
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parts: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(96), nullable=True)
    tool_args: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    tool_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    finish_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    conversation = relationship("AgentConversation", back_populates="messages")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    business_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    agent_conversation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    business_automation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="info") # info, warning, error, debug
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    context: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class AgentLearning(Base):
    __tablename__ = "agent_learnings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    insight: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[int] = mapped_column(SmallInteger, default=80)
    data_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class AiUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    business_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    agent_conversation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    model: Mapped[str] = mapped_column(String(60), default="gemini-3.8")
    context: Mapped[str] = mapped_column(String(60), default="chat")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal("0.000000"))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

