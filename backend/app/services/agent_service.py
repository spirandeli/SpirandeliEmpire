"""SpirandeliEmpire OS 3.1 — Agent Service"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import AgentModel
from app.agents.registry import OFFICIAL_AGENTS, AgentDefinition


class AgentService:
    async def seed_agents_if_needed(self):
        """Seed the 14 official agents into DB if not present."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AgentModel))
            existing = {agent.id: agent for agent in result.scalars().all()}

            for defn in OFFICIAL_AGENTS:
                if defn.id not in existing:
                    agent_db = AgentModel(
                        id=defn.id,
                        name=defn.name,
                        department=defn.department,
                        role=defn.role,
                        specialty=defn.specialty,
                        description=defn.description,
                        system_prompt=defn.system_prompt,
                        provider=defn.provider,
                        model=defn.model,
                        generation_config=defn.generation_config,
                        allowed_tools=defn.allowed_tools,
                        permissions=defn.permissions,
                        operational_state=defn.default_state,
                        office_room=defn.office_room,
                        avatar_url=f"/assets/sprites/{defn.id}.png",
                        metrics={"tasks_completed": 0, "token_usage": 0, "quality_score": 1.0}
                    )
                    session.add(agent_db)
            await session.commit()

    async def list_agents(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AgentModel))
            agents = result.scalars().all()
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "department": a.department,
                    "role": a.role,
                    "specialty": a.specialty,
                    "description": a.description,
                    "model": a.model,
                    "operational_state": a.operational_state,
                    "office_room": a.office_room,
                    "allowed_tools": a.allowed_tools,
                    "metrics": a.metrics or {},
                    "avatar_url": a.avatar_url
                }
                for a in agents
            ]

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            agent = await session.get(AgentModel, agent_id)
            if not agent:
                return None
            return {
                "id": agent.id,
                "name": agent.name,
                "department": agent.department,
                "role": agent.role,
                "specialty": agent.specialty,
                "description": agent.description,
                "system_prompt": agent.system_prompt,
                "model": agent.model,
                "provider": agent.provider,
                "operational_state": agent.operational_state,
                "office_room": agent.office_room,
                "allowed_tools": agent.allowed_tools,
                "permissions": agent.permissions,
                "metrics": agent.metrics or {},
                "history": agent.history or [],
                "assigned_tasks": agent.assigned_tasks or []
            }

    async def update_agent_state(self, agent_id: str, new_state: str):
        async with AsyncSessionLocal() as session:
            agent = await session.get(AgentModel, agent_id)
            if agent:
                agent.operational_state = new_state
                await session.commit()


agent_service = AgentService()

