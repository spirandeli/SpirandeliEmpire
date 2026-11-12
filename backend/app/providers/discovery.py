"""SpirandeliEmpire OS 3.2 — Dynamic Model Discovery & Credential Testing Service"""

import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from app.core.config import settings
from app.core.security import decrypt_secret
from app.database.session import AsyncSessionLocal
from app.database.models import (
    AIProviderCredentialModel,
    AIModelCatalogModel,
    AIProviderSyncLogModel,
)
from app.providers.adapters import get_provider_adapter, ConnectionTestResult


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ModelDiscoveryService:
    async def test_credential(self, user_id: str, credential_id: str) -> ConnectionTestResult:
        async with AsyncSessionLocal() as session:
            cred = await session.get(AIProviderCredentialModel, credential_id)
            if not cred or cred.user_id != user_id:
                raise ValueError("Credencial não encontrada.")

            plain_key = decrypt_secret(cred.encrypted_api_key)
            if not plain_key:
                cred.status = "invalid_credential"
                cred.last_validated_at = _utc_now()
                cred.last_error_message = "Falha ao descriptografar credencial."
                await session.commit()
                return ConnectionTestResult(success=False, status="Invalid Credential", message=cred.last_error_message)

            adapter = get_provider_adapter(cred.provider)
            if cred.provider == "openai":
                res = await adapter.test_connection(plain_key, workspace_org=cred.workspace_org)
            else:
                res = await adapter.test_connection(plain_key)

            cred.last_validated_at = _utc_now()
            cred.last_latency_ms = res.latency_ms
            cred.status = "connected" if res.success else res.status.lower().replace(" ", "_")
            cred.last_error_code = res.error_code
            cred.last_error_message = None if res.success else res.message
            await session.commit()
            return res

    async def sync_models(self, user_id: str, credential_id: str, force: bool = False) -> Dict[str, Any]:
        t0 = time.monotonic()
        async with AsyncSessionLocal() as session:
            cred = await session.get(AIProviderCredentialModel, credential_id)
            if not cred or cred.user_id != user_id:
                raise ValueError("Credencial não encontrada.")

            # Cache check unless force=True
            if not force:
                recent_res = await session.execute(
                    select(AIModelCatalogModel)
                    .where(
                        AIModelCatalogModel.credential_id == credential_id,
                        AIModelCatalogModel.user_id == user_id,
                    )
                    .limit(1)
                )
                first_cached = recent_res.scalar_one_or_none()
                if first_cached and first_cached.last_synced_at:
                    age = _utc_now() - first_cached.last_synced_at
                    if age < timedelta(seconds=settings.MODEL_CATALOG_CACHE_TTL_SECONDS):
                        all_res = await session.execute(
                            select(AIModelCatalogModel).where(
                                AIModelCatalogModel.credential_id == credential_id,
                                AIModelCatalogModel.user_id == user_id,
                            )
                        )
                        items = all_res.scalars().all()
                        return {
                            "credential_id": credential_id,
                            "provider": cred.provider,
                            "cached": True,
                            "models_count": len(items),
                        }

            plain_key = decrypt_secret(cred.encrypted_api_key)
            if not plain_key:
                raise ValueError("Credencial vazia ou inválida.")

            adapter = get_provider_adapter(cred.provider)
            try:
                if cred.provider == "openai":
                    discovered = await adapter.list_models(plain_key, workspace_org=cred.workspace_org)
                else:
                    discovered = await adapter.list_models(plain_key)

                now = _utc_now()
                existing_res = await session.execute(
                    select(AIModelCatalogModel).where(
                        AIModelCatalogModel.credential_id == credential_id,
                        AIModelCatalogModel.user_id == user_id,
                    )
                )
                existing_map = {m.model_id: m for m in existing_res.scalars().all()}
                seen_ids = set()

                for dm in discovered:
                    seen_ids.add(dm.model_id)
                    caps_json = [c.model_dump() for c in dm.capabilities]
                    if dm.model_id in existing_map:
                        row = existing_map[dm.model_id]
                        row.display_name = dm.display_name
                        row.description = dm.description
                        row.version = dm.version
                        row.context_window = dm.context_window
                        row.max_output_tokens = dm.max_output_tokens
                        row.supported_methods = dm.supported_methods
                        row.capabilities = caps_json
                        row.lifecycle_status = dm.lifecycle_status
                        row.is_available = dm.lifecycle_status != "retired"
                        row.raw_metadata = dm.raw_metadata
                        row.last_synced_at = now
                    else:
                        session.add(
                            AIModelCatalogModel(
                                user_id=user_id,
                                credential_id=credential_id,
                                provider=dm.provider,
                                model_id=dm.model_id,
                                display_name=dm.display_name,
                                description=dm.description,
                                version=dm.version,
                                context_window=dm.context_window,
                                max_output_tokens=dm.max_output_tokens,
                                supported_methods=dm.supported_methods,
                                capabilities=caps_json,
                                lifecycle_status=dm.lifecycle_status,
                                is_available=dm.lifecycle_status != "retired",
                                raw_metadata=dm.raw_metadata,
                                last_synced_at=now,
                            )
                        )

                # Mark previously-known models absent from current response as unconfirmed (do NOT delete)
                for mid, row in existing_map.items():
                    if mid not in seen_ids:
                        row.is_available = False
                        row.lifecycle_status = "unconfirmed"

                latency = int((time.monotonic() - t0) * 1000)
                cred.status = "connected"
                cred.last_validated_at = now
                cred.last_latency_ms = latency
                cred.last_error_message = None

                session.add(
                    AIProviderSyncLogModel(
                        user_id=user_id,
                        credential_id=credential_id,
                        provider=cred.provider,
                        status="success",
                        models_count=len(discovered),
                        latency_ms=latency,
                    )
                )
                await session.commit()
                return {
                    "credential_id": credential_id,
                    "provider": cred.provider,
                    "cached": False,
                    "models_count": len(discovered),
                    "latency_ms": latency,
                }
            except Exception as e:
                latency = int((time.monotonic() - t0) * 1000)
                cred.last_error_message = str(e)
                session.add(
                    AIProviderSyncLogModel(
                        user_id=user_id,
                        credential_id=credential_id,
                        provider=cred.provider,
                        status="error",
                        models_count=0,
                        latency_ms=latency,
                        error_message=str(e),
                    )
                )
                await session.commit()
                raise


model_discovery_service = ModelDiscoveryService()

