"""SpirandeliEmpire OS 3.2 — User Profile, Sessions & Admin Management Endpoints"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import UserModel, UserSessionModel, SettingModel, InviteCodeModel
from app.auth.dependencies import (
    get_current_user,
    get_current_user_allow_pw_change,
    require_role,
    log_security_event,
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)
from app.auth.security import (
    verify_password,
    hash_password,
    hash_token,
    create_access_token,
    validate_password_strength,
    generate_opaque_token,
)

router = APIRouter()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


class AdminUserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = Field(default=None, pattern="^(ADMIN|USER|VIEWER)$")


class RegistrationPolicyRequest(BaseModel):
    mode: str = Field(..., pattern="^(public|disabled|invite_only)$")


@router.get("/me")
async def get_profile(current_user: UserModel = Depends(get_current_user_allow_pw_change)):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "must_change_password": current_user.must_change_password,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.patch("/me")
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: UserModel = Depends(get_current_user_allow_pw_change),
):
    async with AsyncSessionLocal() as session:
        user = await session.get(UserModel, current_user.id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        if body.full_name is not None:
            user.full_name = body.full_name.strip()
        await session.commit()
        return {"id": user.id, "full_name": user.full_name, "email": user.email}


@router.patch("/me/password")
async def change_password(
    body: PasswordChangeRequest,
    request: Request,
    response: Response,
    current_user: UserModel = Depends(get_current_user_allow_pw_change),
):
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="As senhas não conferem.")

    # Require >= 12 chars + special/mixed case for mandatory admin first-access change
    is_forced_admin = current_user.must_change_password and current_user.role.upper() in ("ADMIN", "OWNER")
    min_len = 12 if is_forced_admin else 8
    ok, msg = validate_password_strength(body.new_password, min_length=min_len, require_special=is_forced_admin)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    now = _utc_now()
    async with AsyncSessionLocal() as session:
        user = await session.get(UserModel, current_user.id)
        if not user or not verify_password(body.current_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Senha atual incorreta.")
        if verify_password(body.new_password, user.password_hash):
            raise HTTPException(status_code=400, detail="A nova senha deve ser diferente da senha atual.")

        user.password_hash = hash_password(body.new_password)
        user.must_change_password = False
        # Invalidate all previous sessions
        await session.execute(
            update(UserSessionModel).where(UserSessionModel.user_id == user.id).values(is_revoked=True)
        )
        # Issue a fresh active session for the current user
        new_refresh = generate_opaque_token()
        new_sess = UserSessionModel(
            user_id=user.id,
            refresh_token_hash=hash_token(new_refresh),
            user_agent=request.headers.get("user-agent", "")[:512],
            ip_address=request.client.host if request.client else "",
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        session.add(new_sess)
        await session.flush()
        new_access = create_access_token(subject=user.id, role=user.role, session_id=new_sess.id)
        await session.commit()

    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=new_access,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=new_refresh,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    await log_security_event(
        "password_changed",
        user_id=current_user.id,
        ip_address=request.client.host if request.client else "",
    )
    return {
        "status": "password_updated",
        "sessions_revoked": True,
        "access_token": new_access,
        "refresh_token": new_refresh,
    }


@router.get("/me/sessions")
async def list_my_sessions(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserSessionModel)
            .where(UserSessionModel.user_id == current_user.id)
            .order_by(UserSessionModel.created_at.desc())
            .limit(30)
        )
        return [
            {
                "id": s.id,
                "user_agent": s.user_agent,
                "ip_address": s.ip_address,
                "is_revoked": s.is_revoked,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in res.scalars().all()
        ]


@router.delete("/me/sessions/{session_id}")
async def revoke_session(session_id: str, current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        sess = await session.get(UserSessionModel, session_id)
        if not sess or sess.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Sessão não encontrada.")
        sess.is_revoked = True
        await session.commit()
    return {"status": "revoked", "session_id": session_id}


# --- Admin User & Policy Management (never exposes raw API keys) ---

@router.get("/admin/users")
async def admin_list_users(_admin: UserModel = Depends(require_role("ADMIN"))):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(UserModel).order_by(UserModel.created_at.desc()))
        return [
            {
                "id": u.id,
                "full_name": u.full_name,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "must_change_password": u.must_change_password,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in res.scalars().all()
        ]


@router.patch("/admin/users/{user_id}")
async def admin_update_user(
    user_id: str,
    body: AdminUserUpdateRequest,
    _admin: UserModel = Depends(require_role("ADMIN")),
):
    async with AsyncSessionLocal() as session:
        u = await session.get(UserModel, user_id)
        if not u:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        if body.is_active is not None:
            u.is_active = body.is_active
        if body.role is not None:
            u.role = body.role
        await session.commit()
        return {"id": u.id, "role": u.role, "is_active": u.is_active}


@router.get("/admin/policies")
async def admin_get_policies(_admin: UserModel = Depends(require_role("ADMIN"))):
    async with AsyncSessionLocal() as session:
        s = await session.get(SettingModel, "registration_mode")
        mode = (s.value_json.get("mode") if s else None) or settings.REGISTRATION_MODE
        return {"registration_mode": mode}


@router.patch("/admin/policies")
async def admin_update_policies(
    body: RegistrationPolicyRequest,
    _admin: UserModel = Depends(require_role("ADMIN")),
):
    async with AsyncSessionLocal() as session:
        s = await session.get(SettingModel, "registration_mode")
        if s:
            s.value_json = {"mode": body.mode}
        else:
            session.add(
                SettingModel(
                    key="registration_mode",
                    value_json={"mode": body.mode},
                    description="Política de cadastro público",
                )
            )
        await session.commit()
    return {"registration_mode": body.mode}


@router.post("/admin/invites")
async def admin_create_invite(admin: UserModel = Depends(require_role("ADMIN"))):
    code = f"INV-{generate_opaque_token()[:12].upper()}"
    async with AsyncSessionLocal() as session:
        session.add(
            InviteCodeModel(
                code=code,
                created_by_user_id=admin.id,
                expires_at=_utc_now() + timedelta(days=7),
            )
        )
        await session.commit()
    return {"invite_code": code, "expires_in_days": 7}

