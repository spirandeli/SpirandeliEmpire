"""SpirandeliEmpire OS 3.2 — Auth Dependencies, Admin Bootstrap & Gemini Migration"""

import os
from datetime import datetime, timezone
from typing import Callable, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from app.core.config import settings
from app.core.security import encrypt_secret, decrypt_secret
from app.database.session import AsyncSessionLocal
from app.database.models import (
    UserModel,
    UserSessionModel,
    IntegrationModel,
    AIProviderCredentialModel,
    SecurityAuditLogModel,
)
from app.auth.security import decode_access_token, hash_password

bearer_scheme = HTTPBearer(auto_error=False)
ACCESS_COOKIE_NAME = "spirandeli_access"
REFRESH_COOKIE_NAME = "spirandeli_refresh"


async def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: str = "",
    details: Optional[dict] = None,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                SecurityAuditLogModel(
                    user_id=user_id,
                    event_type=event_type,
                    ip_address=ip_address,
                    details_json=details or {},
                )
            )
            await session.commit()
    except Exception:
        pass


async def seed_default_owner_if_needed() -> None:
    """
    1. Bootstrap primary ADMIN account from INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD if configured.
    2. Keep legacy dev owner fallback only if users table is empty and no INITIAL_ADMIN_PASSWORD is set.
    3. Safely migrate existing Gemini API key (IntegrationModel or env) to ADMIN's AIProviderCredentialModel
       without overwriting, printing, or invalidating the original credential.
    """
    admin_user: Optional[UserModel] = None
    async with AsyncSessionLocal() as session:
        if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
            res = await session.execute(
                select(UserModel).where(UserModel.email == settings.INITIAL_ADMIN_EMAIL)
            )
            admin_user = res.scalar_one_or_none()
            if admin_user is None:
                admin_user = UserModel(
                    full_name=settings.INITIAL_ADMIN_NAME,
                    username=settings.INITIAL_ADMIN_EMAIL.split("@")[0][:64],
                    email=settings.INITIAL_ADMIN_EMAIL,
                    password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                    role="ADMIN",
                    is_active=True,
                    must_change_password=True,
                    terms_accepted=True,
                )
                session.add(admin_user)
                await session.commit()
                await session.refresh(admin_user)

        # Legacy fallback for automated test suite / unconfigured dev
        res_any = await session.execute(select(UserModel).limit(1))
        first_user = res_any.scalar_one_or_none()
        if first_user is None:
            fallback_owner = UserModel(
                full_name="Owner",
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="ADMIN",
                is_active=True,
                must_change_password=False,
                terms_accepted=True,
            )
            session.add(fallback_owner)
            await session.commit()
            await session.refresh(fallback_owner)
            admin_user = fallback_owner
        elif admin_user is None:
            res_adm = await session.execute(
                select(UserModel).where(UserModel.role.in_(["ADMIN", "owner"])).limit(1)
            )
            admin_user = res_adm.scalar_one_or_none()

        # Safe Gemini key migration -> ADMIN's AIProviderCredentialModel
        if admin_user is not None:
            existing_cred = await session.execute(
                select(AIProviderCredentialModel).where(
                    AIProviderCredentialModel.user_id == admin_user.id,
                    AIProviderCredentialModel.provider == "gemini",
                ).limit(1)
            )
            if existing_cred.scalar_one_or_none() is None:
                plain_gemini = ""
                integ = await session.get(IntegrationModel, "gemini")
                if integ and integ.credentials_encrypted:
                    plain_gemini = decrypt_secret(integ.credentials_encrypted)
                if not plain_gemini:
                    candidate = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
                    if candidate and not candidate.startswith("mock-"):
                        plain_gemini = candidate

                if plain_gemini:
                    new_cred = AIProviderCredentialModel(
                        user_id=admin_user.id,
                        provider="gemini",
                        label="Gemini Principal (Migrada)",
                        encrypted_api_key=encrypt_secret(plain_gemini, settings.ENCRYPTION_KEY_VERSION),
                        encryption_key_version=settings.ENCRYPTION_KEY_VERSION,
                        status="active",
                        is_default=True,
                        is_active=True,
                    )
                    session.add(new_cred)
                    await session.commit()
                    await session.refresh(new_cred)
                    try:
                        from app.providers.discovery import model_discovery_service
                        await model_discovery_service.sync_models(admin_user.id, new_cred.id, force=True)
                    except Exception:
                        pass


async def get_current_user_allow_pw_change(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UserModel:
    """Authenticate via Bearer JWT or HttpOnly cookie."""
    token: Optional[str] = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif ACCESS_COOKIE_NAME in request.cookies:
        token = request.cookies.get(ACCESS_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with AsyncSessionLocal() as session:
        sid = payload.get("sid")
        if sid:
            sess = await session.get(UserSessionModel, sid)
            if not sess or sess.is_revoked or (sess.expires_at and sess.expires_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None)):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sessão expirada ou revogada.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        user = await session.get(UserModel, payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo ou não encontrado.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


async def get_current_user(
    current_user: UserModel = Depends(get_current_user_allow_pw_change),
) -> UserModel:
    """Block API access if user must complete mandatory first-access password change."""
    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PASSWORD_CHANGE_REQUIRED: Troca obrigatória de senha no primeiro acesso.",
        )
    return current_user


def _is_admin_role(role: str) -> bool:
    return role.upper() in ("ADMIN", "OWNER")


def require_role(*allowed_roles: str) -> Callable:
    """Role-based authorization supporting ADMIN, USER, VIEWER (and legacy owner)."""
    normalized = {r.upper() for r in allowed_roles}
    if "ADMIN" in normalized or "OWNER" in normalized:
        normalized.update({"ADMIN", "OWNER"})

    async def _role_checker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role.upper() not in normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão insuficiente. Requer perfil: {', '.join(allowed_roles)}.",
            )
        return current_user

    return _role_checker
