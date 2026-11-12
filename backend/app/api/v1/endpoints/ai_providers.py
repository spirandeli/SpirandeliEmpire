"""SpirandeliEmpire OS 3.2 — AI Providers Hub (BYOK) Endpoints"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.core.security import encrypt_secret, decrypt_secret, mask_secret
from app.database.session import AsyncSessionLocal
from app.database.models import UserModel, AIProviderCredentialModel
from app.providers.discovery import model_discovery_service

router = APIRouter()

DEFAULT_PROVIDER_META = [
    {"id": "gemini", "name": "Google Gemini"},
    {"id": "openai", "name": "OpenAI"},
    {"id": "anthropic", "name": "Anthropic Claude"},
]


class CreateConnectionRequest(BaseModel):
    provider: str = Field(..., pattern="^(gemini|openai|anthropic)$")
    label: str = Field(..., min_length=1, max_length=128)
    api_key: str = Field(..., min_length=8)
    workspace_org: Optional[str] = Field(default=None, max_length=128)
    is_default: bool = False


class UpdateConnectionRequest(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=128)
    api_key: Optional[str] = Field(default=None, min_length=8)
    workspace_org: Optional[str] = Field(default=None, max_length=128)
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


def _serialize_cred(c: AIProviderCredentialModel) -> dict:
    plain = decrypt_secret(c.encrypted_api_key)
    return {
        "id": c.id,
        "provider": c.provider,
        "label": c.label,
        "workspace_org": c.workspace_org,
        "masked_key": mask_secret(plain) if plain else "********",
        "encryption_key_version": c.encryption_key_version,
        "status": c.status,
        "is_default": c.is_default,
        "is_active": c.is_active,
        "last_validated_at": c.last_validated_at.isoformat() if c.last_validated_at else None,
        "last_latency_ms": c.last_latency_ms,
        "last_error_code": c.last_error_code,
        "last_error_message": c.last_error_message,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/")
async def list_providers_overview(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(AIProviderCredentialModel).where(AIProviderCredentialModel.user_id == current_user.id)
        )
        creds = res.scalars().all()
    by_prov = {p["id"]: [] for p in DEFAULT_PROVIDER_META}
    for c in creds:
        by_prov.setdefault(c.provider, []).append(_serialize_cred(c))
    return [
        {"provider": p["id"], "name": p["name"], "connections": by_prov.get(p["id"], [])}
        for p in DEFAULT_PROVIDER_META
    ]


@router.get("/connections")
async def list_connections(
    provider: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        query = select(AIProviderCredentialModel).where(AIProviderCredentialModel.user_id == current_user.id)
        if provider:
            query = query.where(AIProviderCredentialModel.provider == provider)
        res = await session.execute(query.order_by(AIProviderCredentialModel.created_at.desc()))
        return [_serialize_cred(c) for c in res.scalars().all()]


@router.post("/connections", status_code=status.HTTP_201_CREATED)
async def create_connection(
    body: CreateConnectionRequest,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        if body.is_default:
            await session.execute(
                update(AIProviderCredentialModel)
                .where(
                    AIProviderCredentialModel.user_id == current_user.id,
                    AIProviderCredentialModel.provider == body.provider,
                )
                .values(is_default=False)
            )
        cred = AIProviderCredentialModel(
            user_id=current_user.id,
            provider=body.provider,
            label=body.label.strip(),
            workspace_org=body.workspace_org,
            encrypted_api_key=encrypt_secret(body.api_key.strip(), settings.ENCRYPTION_KEY_VERSION),
            encryption_key_version=settings.ENCRYPTION_KEY_VERSION,
            status="pending",
            is_default=body.is_default,
            is_active=True,
        )
        session.add(cred)
        await session.commit()
        await session.refresh(cred)
        return _serialize_cred(cred)


@router.patch("/connections/{connection_id}")
async def update_connection(
    connection_id: str,
    body: UpdateConnectionRequest,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        cred = await session.get(AIProviderCredentialModel, connection_id)
        if not cred or cred.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Conexão não encontrada.")
        if body.is_default:
            await session.execute(
                update(AIProviderCredentialModel)
                .where(
                    AIProviderCredentialModel.user_id == current_user.id,
                    AIProviderCredentialModel.provider == cred.provider,
                )
                .values(is_default=False)
            )
            cred.is_default = True
        elif body.is_default is False:
            cred.is_default = False
        if body.label is not None:
            cred.label = body.label.strip()
        if body.workspace_org is not None:
            cred.workspace_org = body.workspace_org
        if body.is_active is not None:
            cred.is_active = body.is_active
        if body.api_key is not None:
            cred.encrypted_api_key = encrypt_secret(body.api_key.strip(), settings.ENCRYPTION_KEY_VERSION)
            cred.encryption_key_version = settings.ENCRYPTION_KEY_VERSION
            cred.status = "pending"
            cred.last_error_message = None
        await session.commit()
        await session.refresh(cred)
        return _serialize_cred(cred)


@router.post("/connections/{connection_id}/test")
async def test_connection(
    connection_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    try:
        res = await model_discovery_service.test_credential(current_user.id, connection_id)
        return res.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/connections/{connection_id}/revoke")
async def revoke_connection(
    connection_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        cred = await session.get(AIProviderCredentialModel, connection_id)
        if not cred or cred.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Conexão não encontrada.")
        cred.is_active = False
        cred.status = "revoked"
        cred.encrypted_api_key = ""
        await session.commit()
        return {"id": connection_id, "status": "revoked"}


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        cred = await session.get(AIProviderCredentialModel, connection_id)
        if not cred or cred.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Conexão não encontrada.")
        await session.delete(cred)
        await session.commit()

