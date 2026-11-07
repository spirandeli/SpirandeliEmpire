import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database import get_db
from src.dependencies import get_current_user
from src.models import User, UserIntegration
from src.security import encrypt_secret

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SaveGeminiRequest(BaseModel):
    api_key: str = Field(..., min_length=10)
    model: Optional[str] = "gemini-3.8"


class SaveAppleCaldavRequest(BaseModel):
    apple_id: str
    app_password: str
    server_url: Optional[str] = "https://caldav.icloud.com"


class GenerateShortcutsRequest(BaseModel):
    name: Optional[str] = "Atalhos do iPhone"


def _format_integration(integ: UserIntegration) -> dict[str, Any]:
    return {
        "id": integ.id,
        "provider": integ.provider,
        "label": integ.label,
        "status": integ.status,
        "meta": integ.meta,
        "scopes": integ.scopes,
        "token_prefix": integ.token_prefix,
        "expires_at": integ.expires_at.isoformat() if integ.expires_at else None,
        "last_synced_at": integ.last_synced_at.isoformat() if integ.last_synced_at else None,
        "last_used_at": integ.last_used_at.isoformat() if integ.last_used_at else None,
        "created_at": integ.created_at.isoformat() if integ.created_at else None,
        "updated_at": integ.updated_at.isoformat() if integ.updated_at else None,
    }


@router.get("")
async def index(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(UserIntegration)
        .where(UserIntegration.user_id == current_user.id)
        .order_by(UserIntegration.provider.asc())
    )
    items = res.scalars().all()
    return {"data": [_format_integration(i) for i in items]}


@router.put("/gemini")
async def save_gemini(
    payload: SaveGeminiRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = _utc_now()
    res = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == current_user.id,
            UserIntegration.provider == "gemini",
        )
    )
    integ = res.scalar_one_or_none()

    encrypted_key = encrypt_secret(payload.api_key)
    prefix = payload.api_key[:4] + "..." + payload.api_key[-4:]

    if not integ:
        integ = UserIntegration(
            user_id=current_user.id,
            provider="gemini",
            label="Google Gemini API",
            status="connected",
            credentials=encrypted_key,
            token_prefix=prefix,
            meta={"model": payload.model or "gemini-3.8"},
            created_at=now,
            updated_at=now,
        )
        db.add(integ)
    else:
        integ.credentials = encrypted_key
        integ.token_prefix = prefix
        integ.meta = {"model": payload.model or "gemini-3.8"}
        integ.status = "connected"
        integ.updated_at = now

    await db.commit()
    await db.refresh(integ)

    return {"data": _format_integration(integ)}


@router.put("/apple-caldav")
async def save_apple_caldav(
    payload: SaveAppleCaldavRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = _utc_now()
    res = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == current_user.id,
            UserIntegration.provider == "apple_caldav",
        )
    )
    integ = res.scalar_one_or_none()

    creds = encrypt_secret(payload.app_password)

    if not integ:
        integ = UserIntegration(
            user_id=current_user.id,
            provider="apple_caldav",
            label="Apple iCloud CalDAV",
            status="connected",
            credentials=creds,
            meta={"apple_id": payload.apple_id, "server_url": payload.server_url},
            created_at=now,
            updated_at=now,
        )
        db.add(integ)
    else:
        integ.credentials = creds
        integ.meta = {"apple_id": payload.apple_id, "server_url": payload.server_url}
        integ.status = "connected"
        integ.updated_at = now

    await db.commit()
    await db.refresh(integ)

    return {"data": _format_integration(integ)}


@router.post("/apple-caldav/sync")
async def sync_apple_caldav(
    current_user: User = Depends(get_current_user),
):
    return {"message": "Sincronização do iCloud CalDAV enfileirada no worker."}


@router.post("/shortcuts/token", status_code=status.HTTP_201_CREATED)
async def generate_shortcuts_token(
    payload: Optional[GenerateShortcutsRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = _utc_now()
    plain_token = secrets.token_hex(24)
    token_hash = hashlib.sha256(plain_token.encode("utf-8")).hexdigest()

    res = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == current_user.id,
            UserIntegration.provider == "shortcuts",
        )
    )
    integ = res.scalar_one_or_none()

    if not integ:
        integ = UserIntegration(
            user_id=current_user.id,
            provider="shortcuts",
            label=(payload.name if payload else None) or "Atalhos do iPhone",
            status="connected",
            webhook_token_hash=token_hash,
            created_at=now,
            updated_at=now,
        )
        db.add(integ)
    else:
        integ.webhook_token_hash = token_hash
        integ.updated_at = now

    await db.commit()
    await db.refresh(integ)

    return {
        "data": _format_integration(integ),
        "token": plain_token,
        "webhook_url": "http://localhost:8080/api/webhooks/shortcuts",
        "notice": "Guarde este token agora: ele não será exibido novamente.",
    }


@router.get("/google/redirect")
async def google_redirect(
    current_user: User = Depends(get_current_user),
):
    redirect_url = "https://accounts.google.com/o/oauth2/v2/auth?scope=https://www.googleapis.com/auth/calendar&access_type=offline&response_type=code"
    return {"url": redirect_url}


@router.post("/google/sync")
async def google_sync(
    current_user: User = Depends(get_current_user),
):
    return {"message": "Sincronização com o Google Calendar iniciada."}


@router.get("/google/callback")
async def google_callback():
    return {"message": "Integração com o Google Workspace conectada com sucesso."}


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    integration_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(UserIntegration).where(
            UserIntegration.id == integration_id,
            UserIntegration.user_id == current_user.id,
        )
    )
    integ = res.scalar_one_or_none()
    if integ:
        await db.delete(integ)
        await db.commit()
    return None
