"""SpirandeliEmpire OS 3.1 — Agent Memory API Endpoints"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.auth.dependencies import get_current_user, require_role
from app.database.models import UserModel
from app.memory.service import memory_service

router = APIRouter()


class MemoryCreateRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=64)
    key: str = Field(..., min_length=1, max_length=128)
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="long_term", pattern="^(short_term|long_term|episodic|semantic)$")
    project_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/")
async def list_memories(
    agent_id: Optional[str] = None,
    project_id: Optional[str] = None,
    memory_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
):
    return await memory_service.list_memories(
        agent_id=agent_id,
        project_id=project_id,
        user_id=current_user.id,
        memory_type=memory_type,
        limit=limit,
        offset=offset,
    )


@router.post("/")
async def store_memory(
    body: MemoryCreateRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    return await memory_service.store_memory(
        agent_id=body.agent_id,
        key=body.key,
        content=body.content,
        memory_type=body.memory_type,
        project_id=body.project_id,
        user_id=current_user.id,
        metadata=body.metadata,
    )

