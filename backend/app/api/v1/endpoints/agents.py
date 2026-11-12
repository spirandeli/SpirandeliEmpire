"""SpirandeliEmpire OS 3.1 — Agents API Endpoints"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.auth.dependencies import get_current_user, require_role
from app.database.models import UserModel
from app.services.agent_service import agent_service

router = APIRouter()


class AgentStateUpdate(BaseModel):
    operational_state: str = Field(..., min_length=1, max_length=32)


@router.get("/")
async def list_agents(_user: UserModel = Depends(get_current_user)):
    return await agent_service.list_agents()


@router.get("/{agent_id}")
async def get_agent(agent_id: str, _user: UserModel = Depends(get_current_user)):
    agent = await agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}/state")
async def update_agent_state(
    agent_id: str,
    body: AgentStateUpdate,
    _user: UserModel = Depends(require_role("owner", "admin")),
):
    agent = await agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await agent_service.update_agent_state(agent_id, body.operational_state)
    return {"id": agent_id, "operational_state": body.operational_state}
