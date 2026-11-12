"""SpirandeliEmpire OS 3.1 — Persistent Task Manager Service"""

import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import TaskModel
from app.events.manager import event_system


class TaskService:
    async def create_task(
        self,
        title: str,
        description: str = "",
        assigned_agent_id: str = "jeffrey",
        project_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        priority: str = "medium",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        task_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as session:
            task = TaskModel(
                id=task_id,
                user_id=user_id,
                title=title,
                description=description,
                assigned_agent_id=assigned_agent_id,
                project_id=project_id,
                workflow_id=workflow_id,
                priority=priority,
                status="pending",
            )
            session.add(task)
            await session.commit()

        await event_system.publish(
            event_type="TaskAssigned",
            payload={"task_id": task_id, "title": title, "status": "pending"},
            agent_id=assigned_agent_id,
            project_id=project_id,
            workflow_id=workflow_id,
        )
        return {
            "id": task_id,
            "title": title,
            "description": description,
            "assigned_agent": assigned_agent_id,
            "project_id": project_id,
            "workflow_id": workflow_id,
            "priority": priority,
            "status": "pending",
        }

    async def list_tasks(
        self,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            query = select(TaskModel)
            if user_id:
                query = query.where(TaskModel.user_id == user_id)
            if project_id:
                query = query.where(TaskModel.project_id == project_id)
            if agent_id:
                query = query.where(TaskModel.assigned_agent_id == agent_id)
            if status:
                query = query.where(TaskModel.status == status)

            result = await session.execute(
                query.order_by(TaskModel.created_at.desc()).offset(offset).limit(limit)
            )
            tasks = result.scalars().all()
            return [
                {
                    "id": t.id,
                    "project_id": t.project_id,
                    "workflow_id": t.workflow_id,
                    "title": t.title,
                    "description": t.description,
                    "assigned_agent": t.assigned_agent_id,
                    "status": t.status,
                    "priority": t.priority,
                    "quality_score": t.quality_score,
                    "result_summary": t.result_summary,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ]

    async def get_task(self, task_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            t = await session.get(TaskModel, task_id)
            if not t or (user_id and t.user_id != user_id):
                return None
            return {
                "id": t.id,
                "project_id": t.project_id,
                "workflow_id": t.workflow_id,
                "title": t.title,
                "description": t.description,
                "assigned_agent": t.assigned_agent_id,
                "status": t.status,
                "priority": t.priority,
                "quality_score": t.quality_score,
                "result_summary": t.result_summary,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }

    async def update_task_status(
        self, task_id: str, new_status: str, result_summary: Optional[str] = None, user_id: Optional[str] = None
    ) -> bool:
        async with AsyncSessionLocal() as session:
            task = await session.get(TaskModel, task_id)
            if not task or (user_id and task.user_id != user_id):
                return False
            task.status = new_status
            if result_summary is not None:
                task.result_summary = result_summary
            await session.commit()
            await event_system.publish(
                event_type="TaskCompleted" if new_status == "completed" else "TaskAssigned",
                payload={"task_id": task_id, "status": new_status},
                agent_id=task.assigned_agent_id,
                project_id=task.project_id,
            )
            return True

    async def delete_task(self, task_id: str, user_id: Optional[str] = None) -> bool:
        async with AsyncSessionLocal() as session:
            task = await session.get(TaskModel, task_id)
            if not task or (user_id and task.user_id != user_id):
                return False
            await session.delete(task)
            await session.commit()
            return True


task_service = TaskService()
