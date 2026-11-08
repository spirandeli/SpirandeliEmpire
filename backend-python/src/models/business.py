from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(48), default="custom")
    archetype: Mapped[str] = mapped_column(String(48), default="affiliate_tiktok")
    north_star_metric: Mapped[str] = mapped_column(String(48), default="commission_volume")
    target_kpi_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    webhook_secret_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    niche: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    canvas: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    brand_rules: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    goals: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    acquisition_channels: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    automation_playbook: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    kpis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    automation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user = relationship("User", back_populates="businesses")
    automations = relationship("BusinessAutomation", back_populates="business", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="business", cascade="all, delete-orphan")
    approvals = relationship("ApprovalQueue", back_populates="business", cascade="all, delete-orphan")
    tiktok_products = relationship("TikTokProduct", back_populates="business", cascade="all, delete-orphan")
    content_assets = relationship("ContentAsset", back_populates="business", cascade="all, delete-orphan")


class BusinessAutomation(Base):
    __tablename__ = "business_automations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(64), default="0 */6 * * *")
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_count: Mapped[int] = mapped_column(BigInteger, default=0)
    failure_count: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    business = relationship("Business", back_populates="automations")

