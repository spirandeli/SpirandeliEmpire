from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import (
    BigInteger,
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


class ConversionEvent(Base):
    __tablename__ = "conversion_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    content_asset_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True)
    source_platform: Mapped[str] = mapped_column(String(32), nullable=False) # hotmart, kiwify, tiktok_shop, custom
    event_type: Mapped[str] = mapped_column(String(48), nullable=False) # purchase_approved, abandoned_cart, subscription_renewed, refund
    external_transaction_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    customer_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    payload_raw: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    content_asset = relationship("ContentAsset", back_populates="conversion_events")


class OptimizationCycle(Base):
    __tablename__ = "optimization_cycles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    winning_assets_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    losing_assets_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_diagnosis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actions_taken: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

