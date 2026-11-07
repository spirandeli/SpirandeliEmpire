from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import (
    BigInteger,
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


class TikTokProduct(Base):
    __tablename__ = "tiktok_products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="api")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shop_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affiliate_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    commission_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    sales_velocity: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2), nullable=True)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    margin_score: Mapped[int] = mapped_column(SmallInteger, default=0)
    velocity_score: Mapped[int] = mapped_column(SmallInteger, default=0)
    viral_score: Mapped[int] = mapped_column(SmallInteger, default=0)
    overall_score: Mapped[int] = mapped_column(SmallInteger, default=0)
    status: Mapped[str] = mapped_column(String(24), default="mined")
    raw_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_analysis: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    mined_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    selected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    business = relationship("Business", back_populates="tiktok_products")
    content_assets = relationship("ContentAsset", back_populates="tiktok_product")

