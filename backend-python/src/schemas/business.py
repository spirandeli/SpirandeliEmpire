from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class BusinessCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: Optional[str] = None
    type: Optional[str] = "custom"
    archetype: Optional[str] = "affiliate_tiktok"
    north_star_metric: Optional[str] = "commission_volume"
    target_kpi_value: Optional[Decimal] = Decimal("0.00")
    niche: Optional[str] = None
    description: Optional[str] = None
    canvas: Optional[dict[str, Any]] = None
    brand_rules: Optional[dict[str, Any]] = None
    goals: Optional[dict[str, Any]] = None


class BusinessUpdateRequest(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    target_kpi_value: Optional[Decimal] = None
    canvas: Optional[dict[str, Any]] = None
    brand_rules: Optional[dict[str, Any]] = None
    goals: Optional[dict[str, Any]] = None


class BusinessAutomationCreateRequest(BaseModel):
    type: str
    name: str
    cron_expression: str = "0 */6 * * *"
    timezone: str = "America/Sao_Paulo"
    is_enabled: bool = True
    config: Optional[dict[str, Any]] = None


class BusinessAutomationResponse(BaseModel):
    id: int
    business_id: int
    type: str
    name: str
    cron_expression: str
    timezone: str
    is_enabled: bool
    config: Optional[dict[str, Any]] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    run_count: int = 0
    failure_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BusinessResponse(BaseModel):
    id: int
    name: str
    slug: str
    type: str
    archetype: str
    north_star_metric: str
    target_kpi_value: Decimal
    status: str
    niche: Optional[str] = None
    description: Optional[str] = None
    webhook_secret_token: Optional[str] = None
    canvas: Optional[dict[str, Any]] = None
    brand_rules: Optional[dict[str, Any]] = None
    goals: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

