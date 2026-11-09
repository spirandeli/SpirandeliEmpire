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
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    niche: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    archetype: Optional[str] = None
    north_star_metric: Optional[str] = None
    target_kpi_value: Optional[Decimal] = None
    canvas: Optional[dict[str, Any]] = None
    brand_rules: Optional[dict[str, Any]] = None
    goals: Optional[dict[str, Any]] = None


class ChannelAccountCredentials(BaseModel):
    """Acesso a uma conta de plataforma (YouTube, TikTok...) vinculada ao negócio.

    Para `password` e `api_key_or_token`: omitir/None/"" mantém o valor salvo;
    "__clear__" remove o valor salvo.
    """
    enabled: Optional[bool] = None
    label: Optional[str] = Field(None, max_length=120)
    handle: Optional[str] = Field(None, max_length=255)
    channel_url: Optional[str] = Field(None, max_length=500)
    username_email: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, max_length=500)
    api_key_or_token: Optional[str] = Field(None, max_length=4000)
    notes: Optional[str] = Field(None, max_length=2000)
    auto_publish: Optional[bool] = None


class BusinessChannelsUpdateRequest(BaseModel):
    youtube: Optional[ChannelAccountCredentials] = None
    tiktok: Optional[ChannelAccountCredentials] = None
    instagram: Optional[ChannelAccountCredentials] = None
    custom_platform: Optional[ChannelAccountCredentials] = None


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
    business_model: Optional[str] = None
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


class DarkScriptCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    topic: str = Field(..., min_length=3, max_length=500)
    format_type: str = "short"  # "short" (30-60s) ou "long" (8-12 min)
    target_platform: str = "youtube_shorts"  # "youtube_shorts", "tiktok", "youtube_long"
    tone: Optional[str] = "Misterioso e instigante com suspense crescente"
    visual_style: Optional[str] = "Cinemático hiper-realista 8k, iluminação dramática, Unreal Engine 5 render style"
    voice_persona: Optional[str] = "Voz masculina profunda e documental, ritmo pausado"
    target_audience: Optional[str] = None


class DarkScriptScene(BaseModel):
    scene_number: int
    timestamp: str  # ex: "00:00 - 00:05"
    narration: str
    visual_prompt: str  # Prompt detalhado para Midjourney/Leonardo/Runway
    b_roll_description: str
    on_screen_text: Optional[str] = None


class DarkScriptResponse(BaseModel):
    id: int
    business_id: int
    title: str
    format_type: str
    target_platform: str
    hook: str
    cta: str
    full_narration: str
    scenes: list[DarkScriptScene]
    seo_tags: list[str]
    suggested_music: Optional[str] = None
    voice_persona: Optional[str] = None
    approval_queue_id: Optional[int] = None
    status: str
    created_at: Optional[datetime] = None

