import re
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import Business


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


async def list_user_ventures(db: AsyncSession, user_id: int) -> dict[str, Any]:
    """Lista todos os negócios (ventures) digitais ativos ou em rascunho pertencentes ao usuário.

    Returns:
        Lista detalhada com ID, nome, arquétipo, nicho, métricas e status dos negócios.
    """
    res = await db.execute(
        select(Business).where(Business.user_id == user_id, Business.deleted_at.is_(None)).order_by(Business.id.desc())
    )
    biz_list = res.scalars().all()

    data = []
    for b in biz_list:
        data.append({
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "archetype": b.archetype,
            "status": b.status,
            "niche": b.niche,
            "north_star_metric": b.north_star_metric,
            "target_kpi_value": float(b.target_kpi_value or 0.0),
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })

    return {
        "total_ventures": len(data),
        "ventures": data,
    }


async def create_business_venture(
    db: AsyncSession,
    user_id: int,
    name: str,
    archetype: str = "affiliate_tiktok",
    niche: Optional[str] = None,
    description: Optional[str] = None,
    target_kpi_value: float = 10000.0,
) -> dict[str, Any]:
    """Cria um novo modelo de negócio / empreendimento digital (venture) no SpirandeliEmpire OS.

    Args:
        name: Nome comercial do negócio (ex: 'TikTok Gadgets Brasil').
        archetype: Arquétipo do negócio ('affiliate_tiktok', 'dropshipping', 'saas', 'custom').
        niche: Nicho de mercado (ex: 'Casa Conectada & Iluminação 3D').
        description: Breve descrição ou tese de validação do negócio.
        target_kpi_value: Meta financeira ou de volume (ex: 10000.00).

    Returns:
        Os dados do negócio recém-criado.
    """
    slug_base = _slugify(name)
    slug = f"{slug_base}-{user_id}"

    biz = Business(
        user_id=user_id,
        name=name,
        slug=slug,
        type="digital_venture",
        archetype=archetype,
        niche=niche,
        description=description,
        north_star_metric="commission_volume" if archetype == "affiliate_tiktok" else "revenue",
        target_kpi_value=Decimal(str(target_kpi_value)),
        status="active",
        automation_enabled=True,
        canvas={
            "value_proposition": f"Operação validada no nicho de {niche or 'produtos virais'}",
            "customer_segments": ["Consumidores mobile no TikTok", "Compradores por impulso"],
            "channels": ["TikTok Shop", "Instagram Reels"],
        },
    )
    db.add(biz)
    await db.commit()
    await db.refresh(biz)

    return {
        "success": True,
        "message": f"Negócio '{biz.name}' criado e ativado com sucesso!",
        "business": {
            "id": biz.id,
            "name": biz.name,
            "slug": biz.slug,
            "archetype": biz.archetype,
            "niche": biz.niche,
            "status": biz.status,
            "target_kpi_value": float(biz.target_kpi_value),
        },
    }

