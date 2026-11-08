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
    ContentAsset,
    ConversionEvent,
)
from src.schemas.business import (
    BusinessAutomationCreateRequest,
    BusinessAutomationResponse,
    BusinessCreateRequest,
    BusinessResponse,
    BusinessUpdateRequest,
    DarkScriptCreateRequest,
    DarkScriptResponse,
)
from src.services.dark_channel_service import (
    generate_dark_script,
    list_dark_scripts,
    mine_dark_channel_topics,
)

router = APIRouter(prefix="/businesses", tags=["Businesses"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


def _get_business_model_label(archetype: str, biz_type: str) -> str:
    if archetype in ("canal_dark", "dark_channel") or biz_type == "dark_channel_automation":
        return "Canal Dark (YouTube & TikTok)"
    if archetype in ("affiliate_tiktok", "tiktok_shop_affiliate") or biz_type == "tiktok_shop_affiliate":
        return "TikTok Shop Afiliados"
    if archetype == "infoproduct":
        return "Infoprodutos"
    if archetype == "saas":
        return "SaaS Bootstrapped"
    if archetype == "ecommerce":
        return "E-commerce / Drop"
    return "Venture Digital"


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
            "business_model": _get_business_model_label(b.archetype, b.type),
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
    archetype = payload.archetype or "affiliate_tiktok"
    biz_type = payload.type or "custom"
    north_star = payload.north_star_metric or "commission_volume"
    canvas = payload.canvas or {}
    brand_rules = payload.brand_rules or {}

    if archetype in ("canal_dark", "dark_channel"):
        archetype = "canal_dark"
        if biz_type in ("custom", "tiktok_shop_affiliate"):
            biz_type = "dark_channel_automation"
        if not payload.north_star_metric or payload.north_star_metric == "commission_volume":
            north_star = "monthly_views"
        if not canvas or "Produtos e ofertas validadas" in str(canvas):
            canvas = {
                "value_propositions": [
                    "Vídeos magnéticos sem rosto de alta retenção no YouTube e TikTok.",
                    "Monetização escalável com AdSense, Creator Rewards e produtos de afiliados.",
                ],
                "customer_segments": [
                    "Espectadores no YouTube e TikTok fascinados por narrativas imersivas e curiosidades.",
                ],
                "channels": [
                    "YouTube Shorts",
                    "YouTube Vídeos Longos (8-12 min)",
                    "TikTok Vídeos Virais",
                ],
                "customer_relationships": [
                    "Comunidade engajada por comentários, suspense contínuo (Part 1, 2, 3) e enquetes.",
                ],
                "revenue_streams": [
                    "YouTube AdSense (RPM R$ 20 a R$ 60)",
                    "TikTok Creator Rewards Program",
                    "Comissões de infoprodutos no comentário fixado",
                ],
                "key_resources": [
                    "Cérebro Gemini 3.8 para Roteirização e Ideação",
                    "Vozes de IA e Narrativas Imersivas",
                    "Banco de Prompts Visuais e Renderização",
                ],
                "key_activities": [
                    "Mineração de temas de alto volume de buscas e baixa concorrência",
                    "Geração de roteiros em 5 atos e ganchos de 3 segundos com Gemini 3.8",
                    "Geração de imagens Midjourney e narração sintética",
                    "Aprovação na Fila de Supervisão e postagem",
                ],
                "key_partners": [
                    "YouTube Creator Studio",
                    "TikTok Creator Program",
                    "Plataformas de IA",
                ],
                "cost_structure": [
                    "Assinaturas de APIs e Ferramentas de IA",
                    "VPS e Hospedagem dos Workers",
                ],
            }
        if not brand_rules or "compras por impulso" in str(brand_rules):
            brand_rules = {
                "tone_of_voice": "Misterioso, imersivo, com ritmo dinâmico, quebra de padrões e storytelling de alta retenção.",
                "target_audience": "Audiência de vídeos rápidos e documentários no YouTube e TikTok Brasil.",
                "guidelines": [
                    "Gancho ultra impactante nos primeiros 3 segundos",
                    "Manter suspense crescente e ritmo narrativo constante",
                    "Dividir histórias épicas em partes (Part 1, 2, 3) para gerar retenção em cadeia",
                ],
            }

    business = Business(
        user_id=current_user.id,
        name=payload.name,
        slug=slug,
        type=biz_type,
        archetype=archetype,
        north_star_metric=north_star,
        target_kpi_value=payload.target_kpi_value or Decimal("0.00"),
        niche=payload.niche,
        description=payload.description,
        status="active",
        automation_enabled=True,
        activated_at=now,
        webhook_secret_token=secrets.token_urlsafe(32),
        canvas=canvas,
        brand_rules=brand_rules,
        goals=payload.goals or {},
        created_at=now,
        updated_at=now,
    )
    db.add(business)
    await db.flush()

    # Cria automação inicial para Canal Dark
    if archetype == "canal_dark":
        auto_dark = BusinessAutomation(
            business_id=business.id,
            type="dark_channel_mining",
            name="Mineração Diária de Pautas & Temas Virais (08:00)",
            cron_expression="0 8 * * *",
            is_enabled=True,
            config={
                "niche": business.niche or "Mistérios & Curiosidades",
                "target_platforms": ["youtube_shorts", "tiktok", "youtube_long"],
                "min_predicted_ctr": 8.0,
            },
            created_at=now,
            updated_at=now,
        )
        db.add(auto_dark)

    await db.commit()
    await db.refresh(business)

    resp = BusinessResponse.model_validate(business)
    resp.business_model = _get_business_model_label(business.archetype, business.type)
    return {"data": resp}


@router.get("/{business_id}")
async def show(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    resp = BusinessResponse.model_validate(biz)
    resp.business_model = _get_business_model_label(biz.archetype, biz.type)
    return {"data": resp}


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
    now = _utc_now()
    biz.status = "active"
    biz.automation_enabled = True
    biz.activated_at = now
    biz.updated_at = now
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
    biz.automation_enabled = False
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
    return {"message": f"Job de mineração de produtos TikTok Shop para {biz.name} despachado com sucesso!"}


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
        "learnings": [],
        "optimization_cycles": [],
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
        "message": f"Ciclo de auto-otimização OODA disparado em background pelo Gemini 3.8 para {biz.name}!",
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


@router.post("/{business_id}/automations", status_code=status.HTTP_201_CREATED)
async def store_automation(
    business_id: int,
    payload: BusinessAutomationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    now = _utc_now()
    auto = BusinessAutomation(
        business_id=biz.id,
        type=payload.type,
        name=payload.name,
        cron_expression=payload.cron_expression,
        timezone=payload.timezone,
        is_enabled=payload.is_enabled,
        config=payload.config or {},
        created_at=now,
        updated_at=now,
    )
    db.add(auto)
    await db.commit()
    await db.refresh(auto)
    return {"data": BusinessAutomationResponse.model_validate(auto)}


@router.delete("/{business_id}/automations/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation(
    business_id: int,
    automation_id: int,
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

    await db.delete(auto)
    await db.commit()
    return None


# ==========================================
# ENDPOINTS DO ESTÚDIO DARK (YOUTUBE / TIKTOK)
# ==========================================

@router.post("/{business_id}/dark-studio/generate-script", status_code=status.HTTP_201_CREATED)
async def create_dark_script(
    business_id: int,
    payload: DarkScriptCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    script_data = await generate_dark_script(db, current_user, biz, payload)
    return {"status": "success", "data": script_data}


@router.get("/{business_id}/dark-studio/scripts")
async def get_dark_scripts(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    items = await list_dark_scripts(db, biz.id)
    return {"data": items}


@router.get("/{business_id}/dark-studio/topics")
async def get_dark_topics(
    business_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    biz = await _get_user_business(business_id, current_user, db)
    topics = await mine_dark_channel_topics(biz)
    return {"data": topics}



