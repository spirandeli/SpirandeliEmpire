"""SpirandeliEmpire OS 3.2 — Central Model Resolver, Router & Usage Tracker"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.core.security import decrypt_secret
from app.database.session import AsyncSessionLocal
from app.database.models import (
    AIProviderCredentialModel,
    AIModelCatalogModel,
    UserAIPreferenceModel,
    AgentModelConfigModel,
    TaskModelConfigModel,
    AIUsageRecordModel,
    ProjectModel,
)
from app.providers.adapters import get_provider_adapter, AdapterGenerationResult


class ModelResolutionError(RuntimeError):
    pass


class ResolvedModelSelection(BaseModel):
    user_id: str
    provider: str
    credential_id: str
    model_id: str
    source: str  # explicit_override, project_config, agent_config, task_profile, user_default
    generation_params: Dict[str, Any] = Field(default_factory=dict)
    fallback_enabled: bool = False
    fallback_chain: List[Dict[str, Any]] = Field(default_factory=list)


class ModelResolver:
    async def resolve(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        task_profile: Optional[str] = None,
        project_id: Optional[str] = None,
        explicit_override: Optional[Dict[str, Any]] = None,
        required_capabilities: Optional[List[str]] = None,
    ) -> ResolvedModelSelection:
        """
        Resolve provider/credential/model using strict 5-level precedence:
        1. Explicit override
        2. Project / workflow config
        3. Agent-specific config
        4. Task profile config
        5. User global default
        Never silently defaults to Gemini 2.5 if unconfigured.
        """
        async with AsyncSessionLocal() as session:
            pref = await session.get(UserAIPreferenceModel, user_id)
            agent_cfg = None
            if agent_id:
                res_a = await session.execute(
                    select(AgentModelConfigModel).where(
                        AgentModelConfigModel.user_id == user_id,
                        AgentModelConfigModel.agent_id == agent_id,
                    )
                )
                agent_cfg = res_a.scalar_one_or_none()

            task_cfg = None
            if task_profile:
                res_t = await session.execute(
                    select(TaskModelConfigModel).where(
                        TaskModelConfigModel.user_id == user_id,
                        TaskModelConfigModel.profile_key == task_profile,
                    )
                )
                task_cfg = res_t.scalar_one_or_none()

            proj_cfg = None
            if project_id:
                proj = await session.get(ProjectModel, project_id)
                if proj and proj.user_id == user_id:
                    proj_cfg = (proj.metadata_json or {}).get("model_config")

            fallback_enabled = (
                agent_cfg.fallback_enabled
                if (agent_cfg and agent_cfg.fallback_enabled is not None)
                else (pref.fallback_enabled if pref else False)
            )
            fallback_chain = (
                agent_cfg.fallback_chain
                if (agent_cfg and agent_cfg.fallback_chain)
                else (pref.fallback_chain if pref else [])
            )

            candidates = []
            if explicit_override and explicit_override.get("model_id"):
                candidates.append(("explicit_override", explicit_override))
            if proj_cfg and proj_cfg.get("model_id"):
                candidates.append(("project_config", proj_cfg))
            if agent_cfg and agent_cfg.model_id:
                candidates.append(
                    (
                        "agent_config",
                        {
                            "provider": agent_cfg.provider,
                            "credential_id": agent_cfg.credential_id,
                            "model_id": agent_cfg.model_id,
                            "generation_params": agent_cfg.generation_params or {},
                        },
                    )
                )
            if task_cfg and task_cfg.model_id:
                candidates.append(
                    (
                        "task_profile",
                        {
                            "provider": task_cfg.provider,
                            "credential_id": task_cfg.credential_id,
                            "model_id": task_cfg.model_id,
                            "generation_params": task_cfg.generation_params or {},
                        },
                    )
                )
            if pref and pref.default_model_id:
                candidates.append(
                    (
                        "user_default",
                        {
                            "provider": pref.default_provider,
                            "credential_id": pref.default_credential_id,
                            "model_id": pref.default_model_id,
                            "generation_params": {},
                        },
                    )
                )

            if not candidates:
                raise ModelResolutionError(
                    "Configuration Required: Nenhum modelo padrão ou por agente configurado para este usuário."
                )

            source, chosen = candidates[0]
            provider = chosen.get("provider") or ""
            credential_id = chosen.get("credential_id") or ""
            model_id = chosen["model_id"]

            # Verify credential belongs to user & is active
            cred: Optional[AIProviderCredentialModel] = None
            if credential_id:
                cred = await session.get(AIProviderCredentialModel, credential_id)
                if not cred or cred.user_id != user_id or not cred.is_active:
                    raise ModelResolutionError("Credencial configurada inválida, inativa ou pertence a outro usuário.")
            elif provider:
                res_c = await session.execute(
                    select(AIProviderCredentialModel).where(
                        AIProviderCredentialModel.user_id == user_id,
                        AIProviderCredentialModel.provider == provider,
                        AIProviderCredentialModel.is_active == True,  # noqa: E712
                    ).order_by(AIProviderCredentialModel.is_default.desc())
                )
                cred = res_c.scalar_one_or_none()
                if not cred:
                    raise ModelResolutionError(f"Nenhuma credencial ativa encontrada para o provedor '{provider}'.")
                credential_id = cred.id
            else:
                raise ModelResolutionError("Provider ou credential_id ausente na configuração de modelo.")

            # Validate catalog availability & capabilities if synced
            cat_res = await session.execute(
                select(AIModelCatalogModel).where(
                    AIModelCatalogModel.credential_id == credential_id,
                    AIModelCatalogModel.model_id == model_id,
                )
            )
            cat_model = cat_res.scalar_one_or_none()
            if cat_model:
                if not cat_model.is_available or cat_model.lifecycle_status == "retired":
                    raise ModelResolutionError(f"Modelo '{model_id}' está indisponível ou retired.")
                if required_capabilities:
                    supported_caps = {
                        c["capability"] for c in (cat_model.capabilities or []) if c.get("supported")
                    }
                    missing = [rc for rc in required_capabilities if rc not in supported_caps]
                    if missing:
                        raise ModelResolutionError(
                            f"Modelo '{model_id}' não suporta as capacidades exigidas: {', '.join(missing)}"
                        )

            return ResolvedModelSelection(
                user_id=user_id,
                provider=cred.provider,
                credential_id=credential_id,
                model_id=model_id,
                source=source,
                generation_params=chosen.get("generation_params", {}),
                fallback_enabled=bool(fallback_enabled),
                fallback_chain=list(fallback_chain or []),
            )


class ModelRouter:
    def __init__(self):
        self.resolver = ModelResolver()

    async def _execute_one(
        self,
        user_id: str,
        provider: str,
        credential_id: str,
        model_id: str,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float,
        history: Optional[List[Dict[str, str]]],
    ) -> AdapterGenerationResult:
        async with AsyncSessionLocal() as session:
            cred = await session.get(AIProviderCredentialModel, credential_id)
            if not cred or cred.user_id != user_id or not cred.is_active:
                raise ModelResolutionError("Credencial não autorizada ou inativa.")
            plain_key = decrypt_secret(cred.encrypted_api_key)
            workspace_org = cred.workspace_org
        if not plain_key:
            raise ModelResolutionError("Chave de API vazia ou corrompida.")

        adapter = get_provider_adapter(provider)
        if provider == "openai":
            return await adapter.generate(
                api_key=plain_key,
                model_id=model_id,
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                history=history,
                workspace_org=workspace_org,
            )
        return await adapter.generate(
            api_key=plain_key,
            model_id=model_id,
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            history=history,
        )

    async def _record_usage(
        self,
        user_id: str,
        provider: str,
        model_id: str,
        credential_id: str,
        agent_id: Optional[str],
        project_id: Optional[str],
        workflow_id: Optional[str],
        task_id: Optional[str],
        res: Optional[AdapterGenerationResult],
        status: str,
        fallback_from: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        async with AsyncSessionLocal() as session:
            session.add(
                AIUsageRecordModel(
                    user_id=user_id,
                    agent_id=agent_id,
                    project_id=project_id,
                    workflow_id=workflow_id,
                    task_id=task_id,
                    provider=provider,
                    model_id=model_id,
                    credential_id=credential_id,
                    input_tokens=res.input_tokens if res else 0,
                    output_tokens=res.output_tokens if res else 0,
                    cached_tokens=res.cached_tokens if res else 0,
                    total_tokens=res.total_tokens if res else 0,
                    duration_ms=res.duration_ms if res else 0,
                    status=status,
                    fallback_from=fallback_from,
                    error_message=error_message,
                )
            )
            await session.commit()

    async def generate(
        self,
        user_id: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        agent_id: Optional[str] = None,
        task_profile: Optional[str] = None,
        project_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        task_id: Optional[str] = None,
        explicit_override: Optional[Dict[str, Any]] = None,
        required_capabilities: Optional[List[str]] = None,
        temperature: float = 0.4,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        selection = await self.resolver.resolve(
            user_id=user_id,
            agent_id=agent_id,
            task_profile=task_profile,
            project_id=project_id,
            explicit_override=explicit_override,
            required_capabilities=required_capabilities,
        )
        temp = float(selection.generation_params.get("temperature", temperature))

        try:
            res = await self._execute_one(
                user_id=user_id,
                provider=selection.provider,
                credential_id=selection.credential_id,
                model_id=selection.model_id,
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temp,
                history=history,
            )
            await self._record_usage(
                user_id, selection.provider, selection.model_id, selection.credential_id,
                agent_id, project_id, workflow_id, task_id, res, status="success"
            )
            return {
                "content": res.content,
                "provider": res.provider,
                "model_id": res.model_id,
                "credential_id": selection.credential_id,
                "selection_source": selection.source,
                "total_tokens": res.total_tokens,
                "fallback_used": False,
            }
        except Exception as primary_err:
            await self._record_usage(
                user_id, selection.provider, selection.model_id, selection.credential_id,
                agent_id, project_id, workflow_id, task_id, None, status="error", error_message=str(primary_err)
            )
            if not selection.fallback_enabled or not selection.fallback_chain:
                raise

            # Explicit user-configured fallback chain
            last_err = primary_err
            for fb in selection.fallback_chain:
                fb_prov = fb.get("provider", "")
                fb_cred = fb.get("credential_id", "")
                fb_model = fb.get("model_id", "")
                if not (fb_prov and fb_cred and fb_model):
                    continue
                try:
                    res = await self._execute_one(
                        user_id=user_id,
                        provider=fb_prov,
                        credential_id=fb_cred,
                        model_id=fb_model,
                        prompt=prompt,
                        system_instruction=system_instruction,
                        temperature=temp,
                        history=history,
                    )
                    await self._record_usage(
                        user_id, fb_prov, fb_model, fb_cred,
                        agent_id, project_id, workflow_id, task_id, res,
                        status="fallback_success",
                        fallback_from=f"{selection.provider}:{selection.model_id}",
                    )
                    return {
                        "content": res.content,
                        "provider": res.provider,
                        "model_id": res.model_id,
                        "credential_id": fb_cred,
                        "selection_source": "fallback_chain",
                        "fallback_used": True,
                        "fallback_from": f"{selection.provider}:{selection.model_id}",
                        "original_error": str(primary_err),
                        "total_tokens": res.total_tokens,
                    }
                except Exception as fb_err:
                    last_err = fb_err
            raise last_err


model_router = ModelRouter()

