"""SpirandeliEmpire OS 3.2 — Dynamic AI Models Catalog Endpoints"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from app.auth.dependencies import get_current_user
from app.database.session import AsyncSessionLocal
from app.database.models import UserModel, AIModelCatalogModel
from app.providers.discovery import model_discovery_service

router = APIRouter()


def _serialize_model(m: AIModelCatalogModel) -> dict:
    return {
        "id": m.id,
        "credential_id": m.credential_id,
        "provider": m.provider,
        "model_id": m.model_id,
        "display_name": m.display_name,
        "description": m.description,
        "version": m.version,
        "context_window": m.context_window,
        "max_output_tokens": m.max_output_tokens,
        "supported_methods": m.supported_methods or [],
        "capabilities": m.capabilities or [],
        "lifecycle_status": m.lifecycle_status,
        "is_available": m.is_available,
        "last_synced_at": m.last_synced_at.isoformat() if m.last_synced_at else None,
    }


@router.get("/")
async def list_models(
    provider: Optional[str] = None,
    credential_id: Optional[str] = None,
    capability: Optional[str] = None,
    search: Optional[str] = None,
    only_available: bool = True,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        query = select(AIModelCatalogModel).where(AIModelCatalogModel.user_id == current_user.id)
        if provider:
            query = query.where(AIModelCatalogModel.provider == provider)
        if credential_id:
            query = query.where(AIModelCatalogModel.credential_id == credential_id)
        if only_available:
            query = query.where(AIModelCatalogModel.is_available == True)  # noqa: E712

        res = await session.execute(query.order_by(AIModelCatalogModel.provider.asc(), AIModelCatalogModel.model_id.asc()))
        items = res.scalars().all()

    filtered = []
    search_l = search.lower() if search else None
    for m in items:
        if search_l and search_l not in m.model_id.lower() and search_l not in m.display_name.lower():
            continue
        if capability:
            has_cap = any(
                c.get("capability") == capability and c.get("supported")
                for c in (m.capabilities or [])
            )
            if not has_cap:
                continue
        filtered.append(_serialize_model(m))

    return filtered[offset : offset + limit]


@router.get("/{model_record_id}")
async def get_model_detail(
    model_record_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        m = await session.get(AIModelCatalogModel, model_record_id)
        if not m or m.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Modelo não encontrado.")
        return _serialize_model(m)


@router.post("/sync/{credential_id}")
async def sync_credential_models(
    credential_id: str,
    force: bool = True,
    current_user: UserModel = Depends(get_current_user),
):
    try:
        return await model_discovery_service.sync_models(
            user_id=current_user.id,
            credential_id=credential_id,
            force=force,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha ao sincronizar catálogo: {e}")

