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


class ContentAsset(Base):
    __tablename__ = "content_assets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tracking_code: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True)
    business_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    tiktok_product_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("tiktok_products.id", ondelete="SET NULL"), nullable=True)
    approval_queue_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("approval_queues.id", ondelete="SET NULL"), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("content_assets.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False) # video_script, carousel, hook, copy, caption
    platform: Mapped[str] = mapped_column(String(24), default="tiktok")
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(SmallInteger, default=1)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    funnel_stage: Mapped[str] = mapped_column(String(32), default="tof_attraction")
    angle_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_clicks: Mapped[int] = mapped_column(Integer, default=0)
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    total_sales_count: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue_brl: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    roi_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(24), default="draft")
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    business = relationship("Business", back_populates="content_assets")
    tiktok_product = relationship("TikTokProduct", back_populates="content_assets")
    approval_queue = relationship("ApprovalQueue", back_populates="content_assets")
    conversion_events = relationship("ConversionEvent", back_populates="content_asset")

