"""SpirandeliEmpire OS 3.1 — Integration Hub Service"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import IntegrationModel
from app.core.security import encrypt_secret, decrypt_secret, mask_secret
from app.core.config import settings
from app.providers.gemini_provider import GeminiProvider


class IntegrationService:
    DEFAULT_INTEGRATIONS = [
        {"id": "gemini", "name": "Google Gemini API", "provider": "gemini", "permissions": ["llm_generate", "function_calling"]},
        {"id": "github", "name": "GitHub CI/CD & Repos", "provider": "github", "permissions": ["repo_read", "commit_push"]},
        {"id": "youtube", "name": "YouTube Studio API", "provider": "youtube", "permissions": ["video_upload", "analytics"]},
        {"id": "comfyui", "name": "ComfyUI / Stable Diffusion", "provider": "comfyui", "permissions": ["image_generation"]},
        {"id": "websearch", "name": "Web & RSS Search Engine", "provider": "websearch", "permissions": ["web_read"]},
        {"id": "tts", "name": "Text-to-Speech Engine", "provider": "tts", "permissions": ["audio_synthesis"]}
    ]

    async def seed_integrations_if_needed(self):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(IntegrationModel))
            existing = {i.id: i for i in res.scalars().all()}
            for item in self.DEFAULT_INTEGRATIONS:
                if item["id"] not in existing:
                    # Check if Gemini key already exists in settings
                    encrypted_key = ""
                    status = "pending"
                    if item["id"] == "gemini" and settings.GEMINI_API_KEY:
                        encrypted_key = encrypt_secret(settings.GEMINI_API_KEY)
                        status = "active"

                    integ = IntegrationModel(
                        id=item["id"],
                        name=item["name"],
                        provider=item["provider"],
                        credentials_encrypted=encrypted_key,
                        status=status,
                        permissions=item["permissions"],
                        config_json={"endpoint": "default"}
                    )
                    session.add(integ)
            await session.commit()

    async def list_integrations(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(IntegrationModel))
            integrations = res.scalars().all()
            output = []
            for item in integrations:
                decrypted = decrypt_secret(item.credentials_encrypted)
                output.append({
                    "id": item.id,
                    "name": item.name,
                    "provider": item.provider,
                    "status": item.status,
                    "masked_key": mask_secret(decrypted) if decrypted else "",
                    "has_key": bool(decrypted),
                    "permissions": item.permissions or [],
                    "last_tested_at": item.last_tested_at.isoformat() if item.last_tested_at else None,
                    "last_used_at": item.last_used_at.isoformat() if item.last_used_at else None,
                    "error_message": item.error_message
                })
            return output

    async def save_credentials(self, integration_id: str, credentials_plain: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            integ = await session.get(IntegrationModel, integration_id)
            if not integ:
                integ = IntegrationModel(
                    id=integration_id,
                    name=integration_id.capitalize(),
                    provider=integration_id,
                    status="pending"
                )
                session.add(integ)

            integ.credentials_encrypted = encrypt_secret(credentials_plain)
            integ.status = "active" if credentials_plain else "pending"
            integ.error_message = None
            if config:
                integ.config_json = config
            await session.commit()

            return {
                "id": integ.id,
                "status": integ.status,
                "masked_key": mask_secret(credentials_plain)
            }

    async def test_connection(self, integration_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            integ = await session.get(IntegrationModel, integration_id)
            if not integ:
                return {"success": False, "error": "Integração não encontrada"}

            decrypted = decrypt_secret(integ.credentials_encrypted)
            integ.last_tested_at = datetime.utcnow()

            # Provider-specific test logic
            if integ.provider == "gemini":
                if not decrypted:
                    integ.status = "pending"
                    integ.error_message = "Chave da Gemini API ausente"
                    await session.commit()
                    return {"success": False, "error": integ.error_message}
                
                # Test live call with lightweight token count
                try:
                    test_provider = GeminiProvider(api_key=decrypted)
                    test_res = await test_provider.generate("Ping test", system_instruction="Respond with 'pong'", temperature=0.1)
                    integ.status = "active"
                    integ.error_message = None
                    integ.last_used_at = datetime.utcnow()
                    await session.commit()
                    return {"success": True, "message": "Conexão com Gemini API bem-sucedida!", "model": test_res.model}
                except Exception as e:
                    integ.status = "error"
                    integ.error_message = str(e)
                    await session.commit()
                    return {"success": False, "error": str(e)}

            elif integ.provider == "websearch":
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get("https://api.duckduckgo.com/?q=spirandeli&format=json&no_html=1")
                    if resp.status_code < 400:
                        integ.status = "active"
                        integ.error_message = None
                        integ.last_used_at = datetime.utcnow()
                        await session.commit()
                        return {"success": True, "message": "Web Search Engine acessível."}
                    integ.status = "error"
                    integ.error_message = f"HTTP {resp.status_code}"
                    await session.commit()
                    return {"success": False, "error": integ.error_message}
                except Exception as e:
                    integ.status = "error"
                    integ.error_message = str(e)
                    await session.commit()
                    return {"success": False, "error": str(e)}

            elif integ.provider == "github":
                if not decrypted:
                    integ.status = "pending"
                    integ.error_message = "Token GitHub ausente"
                    await session.commit()
                    return {"success": False, "error": integ.error_message}
                try:
                    async with httpx.AsyncClient(timeout=8.0) as client:
                        resp = await client.get(
                            "https://api.github.com/user",
                            headers={"Authorization": f"Bearer {decrypted}", "Accept": "application/vnd.github+json"},
                        )
                    if resp.status_code == 200:
                        integ.status = "active"
                        integ.error_message = None
                        integ.last_used_at = datetime.utcnow()
                        await session.commit()
                        login = resp.json().get("login", "unknown")
                        return {"success": True, "message": f"GitHub conectado como {login}."}
                    integ.status = "error"
                    integ.error_message = f"GitHub HTTP {resp.status_code}"
                    await session.commit()
                    return {"success": False, "error": integ.error_message}
                except Exception as e:
                    integ.status = "error"
                    integ.error_message = str(e)
                    await session.commit()
                    return {"success": False, "error": str(e)}

            elif integ.provider == "comfyui":
                if not decrypted or not decrypted.startswith(("http://", "https://")):
                    integ.status = "pending" if not decrypted else "error"
                    integ.error_message = "URL do endpoint ComfyUI ausente ou inválida"
                    await session.commit()
                    return {"success": False, "error": integ.error_message}
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(f"{decrypted.rstrip('/')}/system_stats")
                    if resp.status_code == 200:
                        integ.status = "active"
                        integ.error_message = None
                        integ.last_used_at = datetime.utcnow()
                        await session.commit()
                        return {"success": True, "message": "ComfyUI conectado e respondendo."}
                    integ.status = "error"
                    integ.error_message = f"ComfyUI HTTP {resp.status_code}"
                    await session.commit()
                    return {"success": False, "error": integ.error_message}
                except Exception as e:
                    integ.status = "error"
                    integ.error_message = str(e)
                    await session.commit()
                    return {"success": False, "error": str(e)}

            else:
                if not decrypted:
                    integ.status = "pending"
                    integ.error_message = f"Credencial para {integ.name} ausente"
                    await session.commit()
                    return {"success": False, "error": integ.error_message}
                integ.status = "error"
                integ.error_message = f"Verificação ao vivo não suportada para provedor '{integ.provider}' sem conector externo."
                await session.commit()
                return {"success": False, "error": integ.error_message}


integration_service = IntegrationService()

