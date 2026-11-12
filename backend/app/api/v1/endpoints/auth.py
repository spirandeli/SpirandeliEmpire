"""SpirandeliEmpire OS 3.2 — Full Multi-User Authentication Endpoints"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import (
    UserModel,
    UserSessionModel,
    PasswordResetTokenModel,
    InviteCodeModel,
    SettingModel,
)
from app.auth.security import (
    verify_password,
    hash_password,
    validate_password_strength,
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_token,
)
from app.auth.rate_limit import check_rate_limit
from app.auth.dependencies import (
    get_current_user_allow_pw_change,
    log_security_event,
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)

router = APIRouter()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, remember: bool = True) -> None:
    max_age_access = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    max_age_refresh = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400 if remember else None
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=max_age_access,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=max_age_refresh,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=128)
    email: str = Field(..., min_length=5, max_length=256)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    accept_terms: bool = True
    invite_code: Optional[str] = None


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str = Field(..., min_length=1, max_length=128)
    remember_me: bool = True


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=256)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, request: Request):
    ip = _client_ip(request)
    check_rate_limit(f"register:{ip}", max_requests=10, window_seconds=300)

    if not body.accept_terms:
        raise HTTPException(status_code=400, detail="É necessário aceitar os termos de uso.")
    if "@" not in body.email or "." not in body.email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="E-mail inválido.")
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="As senhas não conferem.")

    ok, msg = validate_password_strength(body.password, min_length=8)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    email_norm = body.email.strip().lower()

    async with AsyncSessionLocal() as session:
        # Check registration policy
        policy_setting = await session.get(SettingModel, "registration_mode")
        reg_mode = (policy_setting.value_json.get("mode") if policy_setting else None) or settings.REGISTRATION_MODE
        if reg_mode == "disabled":
            raise HTTPException(status_code=403, detail="Cadastro público desabilitado pelo administrador.")
        if reg_mode == "invite_only":
            if not body.invite_code:
                raise HTTPException(status_code=403, detail="Cadastro permitido apenas por convite.")
            inv_res = await session.execute(
                select(InviteCodeModel).where(
                    InviteCodeModel.code == body.invite_code.strip(),
                    InviteCodeModel.is_used == False,  # noqa: E712
                )
            )
            invite = inv_res.scalar_one_or_none()
            if not invite or (invite.expires_at and invite.expires_at < _utc_now()):
                raise HTTPException(status_code=403, detail="Código de convite inválido ou expirado.")
        else:
            invite = None

        existing = await session.execute(
            select(UserModel).where(UserModel.email == email_norm)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

        base_username = email_norm.split("@")[0][:48]
        username_candidate = base_username
        suffix = 1
        while (await session.execute(select(UserModel).where(UserModel.username == username_candidate))).scalar_one_or_none():
            username_candidate = f"{base_username}_{suffix}"
            suffix += 1

        user = UserModel(
            full_name=body.full_name.strip(),
            username=username_candidate,
            email=email_norm,
            password_hash=hash_password(body.password),
            role="USER",  # Never allow self-assignment to ADMIN
            is_active=True,
            must_change_password=False,
            terms_accepted=True,
        )
        session.add(user)
        await session.flush()

        if invite is not None:
            invite.is_used = True
            invite.used_by_user_id = user.id

        await session.commit()
        await log_security_event("user_registered", user_id=user.id, ip_address=ip, details={"email": email_norm})

        return {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        }


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    ip = _client_ip(request)
    check_rate_limit(f"login:{ip}", max_requests=20, window_seconds=60)

    identifier = (body.email or body.username or "").strip().lower()
    if not identifier:
        raise HTTPException(status_code=400, detail="Informe o e-mail ou usuário.")

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserModel).where(
                (UserModel.email == identifier) | (UserModel.username == identifier)
            )
        )
        user = res.scalar_one_or_none()
        if not user:
            await log_security_event("login_failed_unknown", ip_address=ip, details={"identifier": identifier})
            raise HTTPException(status_code=401, detail="Credenciais inválidas.")

        now = _utc_now()
        if user.locked_until and user.locked_until > now:
            remaining = int((user.locked_until - now).total_seconds())
            raise HTTPException(
                status_code=429,
                detail=f"Conta temporariamente bloqueada por excesso de tentativas. Tente em {remaining}s.",
            )

        if not verify_password(body.password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 10:
                user.locked_until = now + timedelta(minutes=5)
            elif user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(seconds=60)
            await session.commit()
            await log_security_event("login_failed_bad_password", user_id=user.id, ip_address=ip)
            raise HTTPException(status_code=401, detail="Credenciais inválidas.")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Usuário desativado.")

        # Reset brute-force counters
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now

        refresh_raw = generate_opaque_token()
        sess = UserSessionModel(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_raw),
            user_agent=request.headers.get("user-agent", "")[:256],
            ip_address=ip,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        session.add(sess)
        await session.flush()

        access_token = create_access_token(subject=user.id, role=user.role, session_id=sess.id)
        await session.commit()

        _set_auth_cookies(response, access_token, refresh_raw, remember=body.remember_me)
        await log_security_event("login_success", user_id=user.id, ip_address=ip)

        return {
            "access_token": access_token,
            "refresh_token": refresh_raw,
            "token_type": "bearer",
            "must_change_password": user.must_change_password,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "must_change_password": user.must_change_password,
            },
        }


@router.post("/refresh")
async def refresh_session(body: RefreshRequest, request: Request, response: Response):
    raw_refresh = body.refresh_token or request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(status_code=401, detail="Refresh token ausente.")

    token_h = hash_token(raw_refresh)
    now = _utc_now()

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(UserSessionModel).where(UserSessionModel.refresh_token_hash == token_h)
        )
        sess = res.scalar_one_or_none()
        if not sess or sess.is_revoked or sess.expires_at < now:
            raise HTTPException(status_code=401, detail="Sessão expirada ou revogada.")

        user = await session.get(UserModel, sess.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Usuário inativo.")

        # Rotate refresh token
        new_refresh = generate_opaque_token()
        sess.refresh_token_hash = hash_token(new_refresh)
        sess.last_used_at = now
        sess.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_access = create_access_token(subject=user.id, role=user.role, session_id=sess.id)
        await session.commit()

        _set_auth_cookies(response, new_access, new_refresh)
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: UserModel = Depends(get_current_user_allow_pw_change),
):
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    auth_header = request.headers.get("Authorization", "")
    raw_access = auth_header[7:] if auth_header.lower().startswith("bearer ") else request.cookies.get(ACCESS_COOKIE_NAME)
    access_payload = decode_access_token(raw_access) if raw_access else None
    sid = access_payload.get("sid") if access_payload else None

    async with AsyncSessionLocal() as session:
        if raw_refresh:
            await session.execute(
                update(UserSessionModel)
                .where(
                    UserSessionModel.user_id == current_user.id,
                    UserSessionModel.refresh_token_hash == hash_token(raw_refresh),
                )
                .values(is_revoked=True)
            )
        if sid:
            await session.execute(
                update(UserSessionModel)
                .where(
                    UserSessionModel.user_id == current_user.id,
                    UserSessionModel.id == sid,
                )
                .values(is_revoked=True)
            )
        await session.commit()

    _clear_auth_cookies(response)
    await log_security_event("logout", user_id=current_user.id, ip_address=_client_ip(request))
    return {"status": "logged_out"}


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    ip = _client_ip(request)
    check_rate_limit(f"forgot:{ip}", max_requests=5, window_seconds=300)

    email_norm = body.email.strip().lower()
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(UserModel).where(UserModel.email == email_norm))
        user = res.scalar_one_or_none()
        if user:
            raw_token = generate_opaque_token()
            session.add(
                PasswordResetTokenModel(
                    user_id=user.id,
                    token_hash=hash_token(raw_token),
                    expires_at=_utc_now() + timedelta(minutes=30),
                )
            )
            await session.commit()
            await log_security_event("password_reset_requested", user_id=user.id, ip_address=ip)
            # In dev/test mode only, return reset_token hint if DEBUG=True
            if settings.DEBUG:
                return {"message": "Se o e-mail existir, as instruções foram geradas.", "dev_reset_token": raw_token}

    return {"message": "Se o e-mail existir, as instruções foram enviadas."}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, request: Request):
    if body.new_password != body.confirm_password:
        raise HTTPException(status_code=400, detail="As senhas não conferem.")
    ok, msg = validate_password_strength(body.new_password, min_length=8)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    now = _utc_now()
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(PasswordResetTokenModel).where(
                PasswordResetTokenModel.token_hash == hash_token(body.token),
                PasswordResetTokenModel.used_at.is_(None),
            )
        )
        prt = res.scalar_one_or_none()
        if not prt or prt.expires_at < now:
            raise HTTPException(status_code=400, detail="Token de recuperação inválido ou expirado.")

        user = await session.get(UserModel, prt.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")

        user.password_hash = hash_password(body.new_password)
        user.must_change_password = False
        prt.used_at = now
        # Revoke all active sessions after password reset
        await session.execute(
            update(UserSessionModel).where(UserSessionModel.user_id == user.id).values(is_revoked=True)
        )
        await session.commit()
        await log_security_event("password_reset_completed", user_id=user.id, ip_address=_client_ip(request))
        return {"status": "password_reset_ok"}


@router.get("/me")
async def get_me(current_user: UserModel = Depends(get_current_user_allow_pw_change)):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "must_change_password": current_user.must_change_password,
    }
