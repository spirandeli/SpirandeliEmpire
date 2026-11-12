"""SpirandeliEmpire OS 3.2 — Scrypt Password Hashing, Policy & HS256 JWT"""

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Dict, Any, Optional, Tuple
from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash password with memory-hard scrypt + random 16-byte salt."""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=64)
    return f"scrypt$16384$8$1${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored scrypt or legacy pbkdf2_sha256 hash."""
    try:
        if stored_hash.startswith("scrypt$"):
            _, n_s, r_s, p_s, salt_hex, expected_hex = stored_hash.split("$", 5)
            dk = hashlib.scrypt(
                password.encode("utf-8"),
                salt=bytes.fromhex(salt_hex),
                n=int(n_s),
                r=int(r_s),
                p=int(p_s),
                dklen=64,
            )
            return hmac.compare_digest(dk.hex(), expected_hex)

        if stored_hash.startswith("pbkdf2_sha256$"):
            _, salt, expected_hex = stored_hash.split("$", 2)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
            return hmac.compare_digest(dk.hex(), expected_hex)
    except Exception:
        return False
    return False


def validate_password_strength(
    password: str, min_length: int = 8, require_special: bool = False
) -> Tuple[bool, str]:
    if len(password) < min_length:
        return False, f"A senha deve ter pelo menos {min_length} caracteres."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return False, "A senha deve conter letras e números."
    if require_special and (
        not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"[^A-Za-z0-9]", password)
    ):
        return False, "A senha deve conter letras maiúsculas, minúsculas, números e símbolo especial."
    return True, ""


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    subject: str,
    role: str,
    expires_minutes: Optional[int] = None,
    session_id: Optional[str] = None,
) -> str:
    """Create short-lived signed HS256 JWT access token."""
    now = int(time.time())
    ttl = (expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60
    header = {"alg": "HS256", "typ": "JWT"}
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + ttl,
    }
    if session_id:
        payload["sid"] = session_id
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify HS256 JWT signature and expiration."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
