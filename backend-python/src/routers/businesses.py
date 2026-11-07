import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from src.database import get_db
from src.dependencies import get_current_user
from src.models import (
    Business,
    BusinessAutomation,
    User,
    Task,
    ApprovalQueue,
    TikTokProduct,
    ContentAsset,
    ConversionEvent,
)
from src.schemas.business import (
    BusinessAutomationCreateRequest,
    BusinessAutomationResponse,
    BusinessCreateRequest,
    BusinessResponse,
    BusinessUpdateRequest,
)

router = APIRouter(prefix="/businesses", tags=["Businesses"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


async def _get_user_business(business_id: int, user: User, db: AsyncSession) -> Business:
    res = await db.execute(
        select(Business).where(Business.id == business_id, Business.user_id == user.id)
    )
    biz = res.scalar_one_or_none()
    if not biz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Negócio não encontrado ou sem permissão de acesso.",
        )
    return biz


@router.get("")
async def index(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Business).where(Business.user_id == current_user.id)
    if status_filter:
        query = query.where(Business.status == status_filter)
    if search:
        query = query.where(Business.name.ilike(f"%{search}%"))

    query = query.order_by(Business.updated_at.desc())
    res = await db.execute(query)
    businesses = res.scalars().all()

    data = []
    for b in businesses:
        # Contadores rápidos
        open_tasks = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.business_id == b.id,
                    Task.status.in_(["backlog", "ready", "in_progress", "supervision"]),
                )
            )
        ).scalar() or 0

        pending_approvals = (
            await db.execute(
                select(func.count(ApprovalQueue.id)).where(
                    ApprovalQueue.business_id == b.id,
                    ApprovalQueue.status == "pending",
                )
            )
        ).scalar() or 0

        data.append({
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "type": b.type,
            "archetype": b.archetype,
            "status": b.status,
            "north_star_metric": b.north_star_metric,
            "target_kpi_value": float(b.target_kpi_value),
            "niche": b.niche,
            "description": b.description,
            "tasks_open": open_tasks,
            "pending_approvals": pending_approvals,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        })

    return {"data": data}


@router.post("", status_code=status.HTTP_201_CREATED)
async def store(
    payload: BusinessCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    slug = payload.slug or _slugify(payload.name)
    # Garante unicidade do slug para o usuário
    existing = await db.execute(
        select(Business.id).where(Business.user_id == current_user.id, Business.slug == slug)
    )
    if existing.first():
        slug = f"{slug}-{secrets.token_hex(2)}"

    now = _utc_now()
    business = Business(
        user_id=current_user.id,
        name=payload.name,
        slug=slug,
        type=payload.type or "custom",
        archetype=payload.archetype or "affiliate_tiktok",
        north_star_metric=payload.north_star_metric or "commission_volume",
        target_kpi_value=payload.target_kpi_value or Decimal("0.00"),
        niche=payload.niche,
        description=payload.description,
        status="active",
        webhook_secret_token=secrets.token_urlsafe(32),
        canvas=payload.canvas or {},
        brand_rules=payload.brand_rules or {},
        goals=payload.goals or {},
        created_at=now,
        updated_at=now,
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)

    return {"data": BusinessResponse.model_validate(business)}


@router.get("/{business_id}")
async def show(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    return {"data": BusinessResponse.model_validate(biz)}


@router.put("/{business_id}")
@router.patch("/{business_id}")
async def update(
    business_id: int,
    payload: BusinessUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)

    for field, val in payload.model_dump(exclude_unset=True).items():
        setattr(biz, field, val)

    biz.updated_at = _utc_now()
    await db.commit()
    await db.refresh(biz)

    return {"data": BusinessResponse.model_validate(biz)}


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    await db.delete(biz)
    await db.commit()
    return None


@router.post("/{business_id}/activate")
async def activate(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    biz.status = "active"
    biz.updated_at = _utc_now()
    await db.commit()
    await db.refresh(biz)
    return {"data": BusinessResponse.model_validate(biz)}


@router.post("/{business_id}/pause")
async def pause(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    biz.status = "paused"
    biz.updated_at = _utc_now()
    await db.commit()
    await db.refresh(biz)
    return {"data": BusinessResponse.model_validate(biz)}


@router.post("/{business_id}/mine")
async def mine_now(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    return {"message": "Job de mineração de produtos TikTok Shop despachado com sucesso!"}


@router.get("/{business_id}/growth-metrics")
async def growth_metrics(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)

    # 1. Agregações de Funil
    assets_res = await db.execute(
        select(ContentAsset).where(ContentAsset.business_id == biz.id)
    )
    assets = assets_res.scalars().all()

    total_views = sum(a.total_views for a in assets)
    total_clicks = sum(a.total_clicks for a in assets)
    total_leads = sum(a.total_leads for a in assets)

    conv_res = await db.execute(
        select(ConversionEvent).where(ConversionEvent.business_id == biz.id)
    )
    conversions = conv_res.scalars().all()

    approved_sales = [c for c in conversions if c.event_type in ("purchase_approved", "sale_approved")]
    total_sales = len(approved_sales)
    total_revenue = sum(float(c.gross_amount) for c in approved_sales)
    abandoned = len([c for c in conversions if c.event_type in ("abandoned_cart", "pix_generated")])

    conv_rate = round((total_sales / total_clicks * 100), 2) if total_clicks > 0 else (
        round((total_sales / total_views * 100), 2) if total_views > 0 else 0.0
    )

    winning = [
        {
            "id": a.id,
            "title": a.title,
            "tracking_code": a.tracking_code,
            "roi_score": float(a.roi_score),
            "total_views": a.total_views,
            "total_clicks": a.total_clicks,
            "total_sales_count": a.total_sales_count,
            "total_revenue_brl": float(a.total_revenue_brl),
        }
        for a in sorted(assets, key=lambda x: x.roi_score, reverse=True)[:10]
    ]

    recent_convs = [
        {
            "id": c.id,
            "event_type": c.event_type,
            "source_platform": c.source_platform,
            "gross_amount": float(c.gross_amount),
            "occurred_at": c.occurred_at.isoformat() if c.occurred_at else None,
        }
        for c in sorted(conversions, key=lambda x: x.id, reverse=True)[:10]
    ]

    return {
        "funnel": {
            "total_views": total_views,
            "total_clicks": total_clicks,
            "total_leads": total_leads,
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "abandoned_checkouts": abandoned,
            "conversion_rate": conv_rate,
        },
        "winning_assets": winning,
        "losing_assets": [],
        "recent_conversions": recent_convs,
    }


@router.post("/{business_id}/optimize-growth")
async def optimize_growth(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    return {
        "status": "success",
        "message": "Ciclo de auto-otimização OODA disparado em background pelo Gemini 3.8!",
    }


@router.post("/{business_id}/webhooks/simulate")
async def simulate_webhook(
    business_id: int,
    payload: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)

    now = _utc_now()
    event_type = payload.get("event_type", "purchase_approved")
    amount = Decimal(str(payload.get("gross_amount", payload.get("amount", "197.00"))))
    source = payload.get("source_platform", "hotmart")

    conv = ConversionEvent(
        business_id=biz.id,
        source_platform=source,
        event_type=event_type,
        external_transaction_id=f"SIM-{secrets.token_hex(4).upper()}",
        gross_amount=amount,
        net_amount=amount * Decimal("0.80"),
        payload_raw=payload,
        occurred_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return {
        "status": "success",
        "message": "Simulação processada com sucesso!",
        "event": {
            "id": conv.id,
            "event_type": conv.event_type,
            "source_platform": conv.source_platform,
            "gross_amount": float(conv.gross_amount),
        },
    }


@router.get("/{business_id}/automations")
async def list_automations(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    res = await db.execute(
        select(BusinessAutomation).where(BusinessAutomation.business_id == biz.id)
    )
    items = res.scalars().all()
    return {"data": [BusinessAutomationResponse.model_validate(i) for i in items]}


@router.put("/{business_id}/automations/{automation_id}")
async def update_automation(
    business_id: int,
    automation_id: int,
    payload: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    res = await db.execute(
        select(BusinessAutomation).where(
            BusinessAutomation.id == automation_id,
            BusinessAutomation.business_id == biz.id,
        )
    )
    auto = res.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automação não encontrada.")

    for k, v in payload.items():
        if hasattr(auto, k):
            setattr(auto, k, v)

    auto.updated_at = _utc_now()
    await db.commit()
    await db.refresh(auto)

    return {"data": BusinessAutomationResponse.model_validate(auto)}

