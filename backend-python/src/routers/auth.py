from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database import get_db
from src.dependencies import get_current_user
from src.models import Business, User
from src.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserResourceWrapper,
    UserResponse,
)
from src.security import create_sanctum_token, hash_password, verify_password
from src.services.user_onboarding import provision_starter_kit

router = APIRouter(prefix="/auth", tags=["Auth"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Verifica se e-mail já existe
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "O e-mail informado já está cadastrado.",
                "errors": {"email": ["O e-mail informado já está cadastrado."]},
            },
        )

    # Criação do usuário
    user = User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password),
        timezone=payload.timezone or "America/Sao_Paulo",
        created_at=_utc_now(),
        updated_at=_utc_now(),
        last_login_at=_utc_now(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Provisiona starter kit (negócio demonstrativo de alta fidelidade)
    try:
        await provision_starter_kit(user, db)
    except Exception as e:
        print(f"Aviso: Falha ao provisionar starter kit: {e}")

    # Gera token Sanctum
    device = payload.device_name or "webapp"
    token, _ = await create_sanctum_token(user.id, device, db)

    return {
        "user": UserResponse.model_validate(user),
        "token": token,
        "token_type": "Bearer",
    }


@router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == payload.email))
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "As credenciais fornecidas estão incorretas."},
        )

    user.last_login_at = _utc_now()
    await db.commit()

    # Se o usuário não tiver negócios, provisiona starter kit
    biz_count = await db.execute(select(Business.id).where(Business.user_id == user.id))
    if not biz_count.first():
        try:
            await provision_starter_kit(user, db)
        except Exception as e:
            print(f"Aviso: Falha ao provisionar starter kit no login: {e}")

    device = payload.device_name or "webapp"
    token, _ = await create_sanctum_token(user.id, device, db)

    return {
        "user": UserResponse.model_validate(user),
        "token": token,
        "token_type": "Bearer",
    }


@router.get("/me", response_model=UserResourceWrapper)
async def me(current_user: User = Depends(get_current_user)):
    return {"data": UserResponse.model_validate(current_user)}


@router.put("/profile", response_model=UserResourceWrapper)
async def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if payload.name is not None:
        current_user.name = payload.name
    if payload.timezone is not None:
        current_user.timezone = payload.timezone
    if payload.locale is not None:
        current_user.locale = payload.locale
    if payload.agent_enabled is not None:
        current_user.agent_enabled = payload.agent_enabled
    if payload.settings is not None:
        current_user.settings = payload.settings

    current_user.updated_at = _utc_now()
    await db.commit()
    await db.refresh(current_user)

    return {"data": UserResponse.model_validate(current_user)}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    # No caso de Bearer token, a invalidação do lado cliente (remover do LocalStorage)
    # ou exclusão do token no banco encerra a sessão
    return {"message": "Sessão encerrada."}


@router.post("/provision-showcase", status_code=status.HTTP_201_CREATED)
async def provision_showcase(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    business = await provision_starter_kit(current_user, db)
    return {
        "message": "Showcase de demonstração provisionado com sucesso!",
        "business": {
            "id": business.id,
            "name": business.name,
            "slug": business.slug,
            "status": business.status,
            "archetype": business.archetype,
        },
    }
