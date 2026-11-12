"""SpirandeliEmpire OS 3.2 — Authenticated Encryption (AES-256-GCM) & Key Rotation"""

import base64
import hashlib
import os
from typing import Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import settings


def _derive_32b_key(raw_key: str) -> bytes:
    """Derive a deterministic 32-byte key for AES-256-GCM."""
    try:
        decoded = base64.urlsafe_b64decode(raw_key.encode())
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    return hashlib.sha256(raw_key.encode("utf-8")).digest()


def _get_fernet_key(raw_key: str) -> bytes:
    return base64.urlsafe_b64encode(_derive_32b_key(raw_key))


_AES_KEY = _derive_32b_key(settings.ENCRYPTION_MASTER_KEY)
_PREV_AES_KEY = (
    _derive_32b_key(settings.PREVIOUS_ENCRYPTION_MASTER_KEY)
    if settings.PREVIOUS_ENCRYPTION_MASTER_KEY
    else None
)
_LEGACY_FERNET = Fernet(_get_fernet_key(settings.ENCRYPTION_MASTER_KEY))


def encrypt_secret(secret_text: str, key_version: str | None = None) -> str:
    """Encrypt sensitive credentials using AES-256-GCM with versioned envelope."""
    if not secret_text:
        return ""
    ver = key_version or settings.ENCRYPTION_KEY_VERSION or "v1"
    nonce = os.urandom(12)
    aesgcm = AESGCM(_AES_KEY)
    aad = ver.encode("utf-8")
    ct = aesgcm.encrypt(nonce, secret_text.encode("utf-8"), aad)
    return f"gcm:{ver}:{base64.urlsafe_b64encode(nonce).decode()}:{base64.urlsafe_b64encode(ct).decode()}"


def decrypt_secret(encrypted_text: str) -> str:
    """Decrypt AES-256-GCM (current or previous master key) or legacy Fernet tokens."""
    if not encrypted_text:
        return ""

    if encrypted_text.startswith("gcm:"):
        try:
            _, ver, nonce_b64, ct_b64 = encrypted_text.split(":", 3)
            nonce = base64.urlsafe_b64decode(nonce_b64.encode())
            ct = base64.urlsafe_b64decode(ct_b64.encode())
            aad = ver.encode("utf-8")
            for key in (_AES_KEY, _PREV_AES_KEY):
                if key is None:
                    continue
                try:
                    return AESGCM(key).decrypt(nonce, ct, aad).decode("utf-8")
                except Exception:
                    continue
            return ""
        except Exception:
            return ""

    # Legacy Fernet compatibility (preserves existing DB IntegrationModel secrets)
    try:
        return _LEGACY_FERNET.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def rotate_encrypted_secret(encrypted_text: str, new_version: str) -> Tuple[str, str]:
    """Re-encrypt an existing credential under the current master key and new version."""
    plain = decrypt_secret(encrypted_text)
    if not plain:
        raise ValueError("Unable to decrypt credential with current or previous master key.")
    return encrypt_secret(plain, key_version=new_version), new_version


def mask_secret(secret_text: str) -> str:
    """Return masked representation safe for UI responses (e.g. sk-****1234)."""
    if not secret_text:
        return ""
    if len(secret_text) <= 8:
        return "********"
    return f"{secret_text[:4]}****{secret_text[-4:]}"
