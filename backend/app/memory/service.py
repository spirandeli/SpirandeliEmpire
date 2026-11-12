"""SpirandeliEmpire OS 3.1 — Persistent Agent Memory Service"""

from typing import List, Dict, Any, Optional
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import MemoryModel


class MemoryService:
    async def store_memory(
        self,
        agent_id: str,
        key: str,
        content: str,
        memory_type: str = "long_term",
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            existing_res = await session.execute(
                select(MemoryModel).where(
                    MemoryModel.agent_id == agent_id,
                    MemoryModel.key == key,
                    MemoryModel.project_id == project_id,
                    MemoryModel.user_id == user_id,
                )
            )
            mem = existing_res.scalar_one_or_none()
            if mem:
                mem.content = content
                mem.memory_type = memory_type
                if metadata is not None:
                    mem.metadata_json = metadata
            else:
                mem = MemoryModel(
                    user_id=user_id,
                    agent_id=agent_id,
                    project_id=project_id,
                    memory_type=memory_type,
                    key=key,
                    content=content,
                    metadata_json=metadata or {},
                )
                session.add(mem)
            await session.commit()
            return {
                "id": mem.id,
                "agent_id": mem.agent_id,
                "project_id": mem.project_id,
                "memory_type": mem.memory_type,
                "key": mem.key,
                "content": mem.content,
            }

    async def list_memories(
        self,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            query = select(MemoryModel)
            if user_id:
                query = query.where(MemoryModel.user_id == user_id)
            if agent_id:
                query = query.where(MemoryModel.agent_id == agent_id)
            if project_id:
                query = query.where(MemoryModel.project_id == project_id)
            if memory_type:
                query = query.where(MemoryModel.memory_type == memory_type)
            res = await session.execute(
                query.order_by(MemoryModel.updated_at.desc()).offset(offset).limit(limit)
            )
            return [
                {
                    "id": m.id,
                    "agent_id": m.agent_id,
                    "project_id": m.project_id,
                    "memory_type": m.memory_type,
                    "key": m.key,
                    "content": m.content,
                    "metadata": m.metadata_json or {},
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                }
                for m in res.scalars().all()
            ]


memory_service = MemoryService()

