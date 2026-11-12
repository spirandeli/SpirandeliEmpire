"""SpirandeliEmpire OS 3.2 — API v1 Router Aggregator"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    ai_providers,
    ai_models,
    ai_settings,
    ai_usage,
    agents,
    projects,
    tasks,
    workflows,
    artifacts,
    approvals,
    integrations,
    chat,
    memory,
    system,
    websocket,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users & Security"])
api_router.include_router(ai_providers.router, prefix="/ai-providers", tags=["AI Providers (BYOK)"])
api_router.include_router(ai_models.router, prefix="/ai-models", tags=["AI Models Catalog"])
api_router.include_router(ai_settings.router, prefix="/ai-settings", tags=["AI Model Manager"])
api_router.include_router(ai_usage.router, prefix="/ai-usage", tags=["AI Usage & Costs"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["Artifacts"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat with Jeffrey"])
api_router.include_router(memory.router, prefix="/memory", tags=["Agent Memory"])
api_router.include_router(system.router, prefix="/system", tags=["System & VPS"])
api_router.include_router(websocket.router, tags=["WebSockets"])
