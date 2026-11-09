"""
Cofre de credenciais de canais por negócio (YouTube, TikTok, Instagram, etc.).

As credenciais ficam na coluna JSON `businesses.acquisition_channels`, no formato:

    {
        "youtube": {"enabled": true, "handle": "@canal", "password": "<cifrado>", ...},
        "tiktok":  {...},
    }

Campos sensíveis (SECRET_FIELDS) são sempre persistidos criptografados com
`encrypt_secret` (AES-256-CBC + HMAC, compatível com Laravel Crypt) e nunca
são retornados em texto puro pelos endpoints de leitura geral do negócio.
"""
from typing import Any, Optional

from src.models import Business
from src.security import decrypt_secret, encrypt_secret

SUPPORTED_PLATFORMS = ("youtube", "tiktok", "instagram", "custom_platform")
SECRET_FIELDS = ("password", "api_key_or_token")
PUBLIC_FIELDS = (
    "enabled",
    "label",
    "handle",
    "channel_url",
    "username_email",
    "notes",
    "auto_publish",
)


def _safe_decrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return decrypt_secret(value)
    except Exception:
        # Valor corrompido ou cifrado com outra APP_KEY: não vaza o conteúdo bruto
        return None


def _raw_channels(biz: Business) -> dict[str, Any]:
    raw = biz.acquisition_channels
    return dict(raw) if isinstance(raw, dict) else {}


def summarize_channels(biz: Business) -> dict[str, dict[str, Any]]:
    """Visão segura (sem segredos) de todos os canais suportados."""
    raw = _raw_channels(biz)
    summary: dict[str, dict[str, Any]] = {}
    for platform in SUPPORTED_PLATFORMS:
        data = raw.get(platform) if isinstance(raw.get(platform), dict) else {}
        item = {field: data.get(field) for field in PUBLIC_FIELDS}
        item["enabled"] = bool(data.get("enabled", False))
        item["auto_publish"] = bool(data.get("auto_publish", False))
        item["has_password"] = bool(data.get("password"))
        item["has_api_key_or_token"] = bool(data.get("api_key_or_token"))
        item["configured"] = bool(data.get("username_email") or data.get("handle")) and (
            item["has_password"] or item["has_api_key_or_token"]
        )
        item["updated_at"] = data.get("updated_at")
        summary[platform] = item
    return summary


def configured_platforms(biz: Business) -> list[str]:
    return [p for p, item in summarize_channels(biz).items() if item["configured"]]


def reveal_channels(biz: Business) -> dict[str, dict[str, Any]]:
    """Visão completa com segredos descriptografados (apenas para o dono autenticado)."""
    raw = _raw_channels(biz)
    summary = summarize_channels(biz)
    for platform, item in summary.items():
        data = raw.get(platform) if isinstance(raw.get(platform), dict) else {}
        for field in SECRET_FIELDS:
            item[field] = _safe_decrypt(data.get(field))
    return summary


def get_platform_credentials(biz: Business, platform: str) -> Optional[dict[str, Any]]:
    """
    Helper para workers/integrações: retorna as credenciais descriptografadas de
    uma plataforma, ou None se ela não estiver habilitada.
    """
    if platform not in SUPPORTED_PLATFORMS:
        return None
    item = reveal_channels(biz).get(platform)
    if not item or not item.get("enabled"):
        return None
    return item


def merge_channel_updates(
    biz: Business,
    updates: dict[str, dict[str, Any]],
    now_iso: str,
) -> dict[str, Any]:
    """
    Mescla atualizações nos canais existentes.

    Regras para campos sensíveis:
      - ausente / None / ""  -> mantém o valor já armazenado
      - "__clear__"          -> remove o valor armazenado
      - qualquer outro texto -> criptografa e substitui
    """
    raw = _raw_channels(biz)
    for platform, payload in updates.items():
        if platform not in SUPPORTED_PLATFORMS or payload is None:
            continue
        current = dict(raw.get(platform) or {})
        for field in PUBLIC_FIELDS:
            if field in payload:
                current[field] = payload[field]
        for field in SECRET_FIELDS:
            new_val = payload.get(field)
            if new_val is None or new_val == "":
                continue
            if new_val == "__clear__":
                current.pop(field, None)
            else:
                current[field] = encrypt_secret(str(new_val))
        current["updated_at"] = now_iso
        raw[platform] = current
    return raw

