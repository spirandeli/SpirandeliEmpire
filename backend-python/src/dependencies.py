from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models import User
from src.security import authenticate_token

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Forneça um Bearer Token válido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await authenticate_token(credentials.credentials, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores do sistema.",
        )
    return current_user


async def verify_ai_access(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_ai_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="O kill-switch de IA está ativo para a sua conta. Operações com o Gemini estão suspensas.",
        )
    if current_user.tokens_used_this_month >= current_user.monthly_token_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Limite mensal de tokens de IA atingido. Solicite expansão ao administrador.",
        )
    return current_user

