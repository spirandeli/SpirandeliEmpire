import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.config import get_settings
from src.crypto_laravel import (
    decrypt_string as laravel_decrypt,
    encrypt_string as laravel_encrypt,
)
from src.models import PersonalAccessToken, User

settings = get_settings()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    """Gera hash bcrypt compatível com o Laravel."""
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha garantindo compatibilidade com hashes $2y$ (PHP) e $2b$ (Python)."""
    try:
        pw_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        # PHP usa $2y$, bcrypt em Python usa $2b$
        if hash_bytes.startswith(b"$2y$"):
            hash_bytes = b"$2b$" + hash_bytes[4:]
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False


async def create_sanctum_token(
    user_id: int,
    name: str = "webapp",
    db: Optional[AsyncSession] = None,
) -> Tuple[str, PersonalAccessToken]:
    """
    Gera um Personal Access Token rigorosamente idêntico ao Laravel Sanctum:
    Formato retornado ao cliente: '{id}|{plainTextToken}'
    Armazenado no banco: sha256(plainTextToken)
    """
    plain_token = secrets.token_hex(20) # 40 caracteres hex
    token_hash = hashlib.sha256(plain_token.encode("utf-8")).hexdigest()

    token_record = PersonalAccessToken(
        tokenable_type="App\\Models\\User",
        tokenable_id=user_id,
        name=name,
        token=token_hash,
        abilities='["*"]',
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )

    if db:
        db.add(token_record)
        await db.commit()
        await db.refresh(token_record)
        client_token = f"{token_record.id}|{plain_token}"
        return client_token, token_record

    return plain_token, token_record


async def authenticate_token(token_str: str, db: AsyncSession) -> Optional[User]:
    """
    Valida token Bearer no formato Sanctum ('{id}|{plain_token}') ou token hash direto.
    """
    if not token_str:
        return None

    if "|" in token_str:
        token_id_str, plain_token = token_str.split("|", 1)
        try:
            token_id = int(token_id_str)
        except ValueError:
            return None
        token_hash = hashlib.sha256(plain_token.encode("utf-8")).hexdigest()

        query = select(PersonalAccessToken).where(
            PersonalAccessToken.id == token_id,
            PersonalAccessToken.token == token_hash,
        )
    else:
        # Fallback para token direto
        token_hash = hashlib.sha256(token_str.encode("utf-8")).hexdigest()
        query = select(PersonalAccessToken).where(
            PersonalAccessToken.token == token_hash,
        )

    res = await db.execute(query)
    token_record = res.scalar_one_or_none()

    if not token_record:
        return None

    # Atualiza timestamp de último uso
    token_record.last_used_at = _utc_now()
    await db.commit()

    # Busca o usuário associado
    user_res = await db.execute(select(User).where(User.id == token_record.tokenable_id))
    return user_res.scalar_one_or_none()


def encrypt_secret(plain_text: str) -> str:
    """Criptografa dado sensível usando APP_KEY do Laravel."""
    return laravel_encrypt(plain_text, settings.APP_KEY)


def decrypt_secret(encrypted_text: str) -> str:
    """Descriptografa dado sensível usando APP_KEY do Laravel."""
    return laravel_decrypt(encrypted_text, settings.APP_KEY)
