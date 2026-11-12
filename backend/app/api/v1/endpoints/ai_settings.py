"""SpirandeliEmpire OS 3.2 — User AI Settings (Global, 14 Agents, Task Profiles & Fallback)"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from app.agents.registry import OFFICIAL_AGENTS
from app.auth.dependencies import get_current_user
from app.database.session import AsyncSessionLocal
from app.database.models import (
    UserModel,
    UserAIPreferenceModel,
    AgentModelConfigModel,
    TaskModelConfigModel,
)

router = APIRouter()

DEFAULT_TASK_PROFILES = [
    {"profile_key": "complex_planning", "display_name": "Planejamento Complexo"},
    {"profile_key": "reasoning", "display_name": "Raciocínio"},
    {"profile_key": "coding", "display_name": "Programação"},
    {"profile_key": "code_review", "display_name": "Revisão de Código"},
    {"profile_key": "research", "display_name": "Pesquisa"},
    {"profile_key": "writing", "display_name": "Escrita"},
    {"profile_key": "summarization", "display_name": "Resumo"},
    {"profile_key": "image_analysis", "display_name": "Análise de Imagens"},
    {"profile_key": "transcription", "display_name": "Transcrição"},
    {"profile_key": "fast_tasks", "display_name": "Tarefas Rápidas"},
    {"profile_key": "cost_efficient", "display_name": "Tarefas Econômicas"},
]


class GlobalAISettingsUpdate(BaseModel):
    default_provider: Optional[str] = None
    default_credential_id: Optional[str] = None
    default_model_id: Optional[str] = None
    fallback_enabled: Optional[bool] = None
    fallback_chain: Optional[List[Dict[str, Any]]] = None
    usage_limits: Optional[Dict[str, Any]] = None


class AgentModelConfigUpdate(BaseModel):
    provider: Optional[str] = None
    credential_id: Optional[str] = None
    model_id: Optional[str] = None
    generation_params: Optional[Dict[str, Any]] = None
    fallback_enabled: Optional[bool] = None
    fallback_chain: Optional[List[Dict[str, Any]]] = None


class TaskProfileConfigUpdate(BaseModel):
    provider: Optional[str] = None
    credential_id: Optional[str] = None
    model_id: Optional[str] = None
    generation_params: Optional[Dict[str, Any]] = None


class FallbackUpdate(BaseModel):
    fallback_enabled: bool
    fallback_chain: List[Dict[str, Any]] = []


@router.get("/")
async def get_global_ai_settings(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        pref = await session.get(UserAIPreferenceModel, current_user.id)
        if not pref:
            return {
                "user_id": current_user.id,
                "default_provider": None,
                "default_credential_id": None,
                "default_model_id": None,
                "fallback_enabled": False,
                "fallback_chain": [],
                "usage_limits": {},
            }
        return {
            "user_id": pref.user_id,
            "default_provider": pref.default_provider,
            "default_credential_id": pref.default_credential_id,
            "default_model_id": pref.default_model_id,
            "fallback_enabled": pref.fallback_enabled,
            "fallback_chain": pref.fallback_chain or [],
            "usage_limits": pref.usage_limits or {},
        }


@router.patch("/")
async def update_global_ai_settings(
    body: GlobalAISettingsUpdate,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        pref = await session.get(UserAIPreferenceModel, current_user.id)
        if not pref:
            pref = UserAIPreferenceModel(user_id=current_user.id)
            session.add(pref)
        for field in (
            "default_provider", "default_credential_id", "default_model_id",
            "fallback_enabled", "fallback_chain", "usage_limits"
        ):
            val = getattr(body, field)
            if val is not None:
                setattr(pref, field, val)
        await session.commit()
        return {
            "user_id": pref.user_id,
            "default_provider": pref.default_provider,
            "default_credential_id": pref.default_credential_id,
            "default_model_id": pref.default_model_id,
            "fallback_enabled": pref.fallback_enabled,
            "fallback_chain": pref.fallback_chain or [],
            "usage_limits": pref.usage_limits or {},
        }


@router.get("/agents")
async def list_agent_model_configs(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(AgentModelConfigModel).where(AgentModelConfigModel.user_id == current_user.id)
        )
        cfg_map = {c.agent_id: c for c in res.scalars().all()}

    output = []
    for ag in OFFICIAL_AGENTS:
        cfg = cfg_map.get(ag.id)
        output.append({
            "agent_id": ag.id,
            "agent_name": ag.name,
            "department": ag.department,
            "role": ag.role,
            "provider": cfg.provider if cfg else None,
            "credential_id": cfg.credential_id if cfg else None,
            "model_id": cfg.model_id if cfg else None,
            "generation_params": cfg.generation_params if cfg else ag.generation_config,
            "fallback_enabled": cfg.fallback_enabled if cfg else None,
            "fallback_chain": cfg.fallback_chain if cfg else [],
        })
    return output


@router.patch("/agents/{agent_id}")
async def update_agent_model_config(
    agent_id: str,
    body: AgentModelConfigUpdate,
    current_user: UserModel = Depends(get_current_user),
):
    if not any(a.id == agent_id for a in OFFICIAL_AGENTS):
        raise HTTPException(status_code=404, detail="Agente não encontrado.")

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(AgentModelConfigModel).where(
                AgentModelConfigModel.user_id == current_user.id,
                AgentModelConfigModel.agent_id == agent_id,
            )
        )
        cfg = res.scalar_one_or_none()
        if not cfg:
            cfg = AgentModelConfigModel(user_id=current_user.id, agent_id=agent_id)
            session.add(cfg)
        for field in ("provider", "credential_id", "model_id", "generation_params", "fallback_enabled", "fallback_chain"):
            val = getattr(body, field)
            if val is not None:
                setattr(cfg, field, val)
        await session.commit()
        return {
            "agent_id": agent_id,
            "provider": cfg.provider,
            "credential_id": cfg.credential_id,
            "model_id": cfg.model_id,
            "generation_params": cfg.generation_params or {},
            "fallback_enabled": cfg.fallback_enabled,
        }


@router.get("/task-profiles")
async def list_task_profiles(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(TaskModelConfigModel).where(TaskModelConfigModel.user_id == current_user.id)
        )
        cfg_map = {t.profile_key: t for t in res.scalars().all()}

    return [
        {
            "profile_key": p["profile_key"],
            "display_name": p["display_name"],
            "provider": cfg_map[p["profile_key"]].provider if p["profile_key"] in cfg_map else None,
            "credential_id": cfg_map[p["profile_key"]].credential_id if p["profile_key"] in cfg_map else None,
            "model_id": cfg_map[p["profile_key"]].model_id if p["profile_key"] in cfg_map else None,
            "generation_params": cfg_map[p["profile_key"]].generation_params if p["profile_key"] in cfg_map else {},
        }
        for p in DEFAULT_TASK_PROFILES
    ]


@router.patch("/task-profiles/{profile_key}")
async def update_task_profile(
    profile_key: str,
    body: TaskProfileConfigUpdate,
    current_user: UserModel = Depends(get_current_user),
):
    profile_meta = next((p for p in DEFAULT_TASK_PROFILES if p["profile_key"] == profile_key), None)
    if not profile_meta:
        raise HTTPException(status_code=404, detail="Perfil de tarefa inválido.")

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(TaskModelConfigModel).where(
                TaskModelConfigModel.user_id == current_user.id,
                TaskModelConfigModel.profile_key == profile_key,
            )
        )
        cfg = res.scalar_one_or_none()
        if not cfg:
            cfg = TaskModelConfigModel(
                user_id=current_user.id,
                profile_key=profile_key,
                display_name=profile_meta["display_name"],
            )
            session.add(cfg)
        for field in ("provider", "credential_id", "model_id", "generation_params"):
            val = getattr(body, field)
            if val is not None:
                setattr(cfg, field, val)
        await session.commit()
        return {
            "profile_key": profile_key,
            "display_name": cfg.display_name,
            "provider": cfg.provider,
            "credential_id": cfg.credential_id,
            "model_id": cfg.model_id,
        }


@router.get("/fallback")
async def get_fallback_settings(current_user: UserModel = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        pref = await session.get(UserAIPreferenceModel, current_user.id)
        return {
            "fallback_enabled": pref.fallback_enabled if pref else False,
            "fallback_chain": (pref.fallback_chain or []) if pref else [],
        }


@router.patch("/fallback")
async def update_fallback_settings(
    body: FallbackUpdate,
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        pref = await session.get(UserAIPreferenceModel, current_user.id)
        if not pref:
            pref = UserAIPreferenceModel(user_id=current_user.id)
            session.add(pref)
        pref.fallback_enabled = body.fallback_enabled
        pref.fallback_chain = body.fallback_chain
        await session.commit()
        return {"fallback_enabled": pref.fallback_enabled, "fallback_chain": pref.fallback_chain}

