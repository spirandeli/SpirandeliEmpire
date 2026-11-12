"""SpirandeliEmpire OS 3.1 — Project Hub & Business Wizard Service"""

import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import ProjectModel, TaskModel, WorkflowModel, ArtifactModel
from app.orchestrator.workflows.manager import workflow_manager
from app.events.manager import event_system


class ProjectService:
    async def create_project(
        self,
        name: str,
        description: str,
        project_type: str = "software",
        priority: str = "medium",
        department: str = "development",
        objectives: Optional[List[str]] = None,
        lead_agent_id: str = "jeffrey",
        auto_start_workflow: bool = True,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        project_id = str(uuid.uuid4())
        objs = objectives or [f"Concluir implementação e entrega com sucesso de {name}"]

        async with AsyncSessionLocal() as session:
            project = ProjectModel(
                id=project_id,
                user_id=user_id,
                name=name,
                description=description,
                objectives=objs,
                project_type=project_type,
                status="active",
                priority=priority,
                department=department,
                lead_agent_id=lead_agent_id
            )
            session.add(project)
            await session.commit()

        await event_system.publish(
            event_type="ProjectCreated",
            payload={"project_id": project_id, "name": name, "type": project_type},
            project_id=project_id
        )

        wf_res = None
        if auto_start_workflow:
            wf_map = {
                "software": "development",
                "content": "content",
                "audiovisual": "clip",
                "business": "business"
            }
            wf_type = wf_map.get(project_type, "supervisor")
            wf_res = await workflow_manager.start_workflow(
                user_request=f"Executar projeto '{name}': {description}",
                workflow_type=wf_type,
                project_id=project_id,
                user_id=user_id,
            )

        return {
            "id": project_id,
            "name": name,
            "description": description,
            "project_type": project_type,
            "status": "active",
            "priority": priority,
            "department": department,
            "lead_agent_id": lead_agent_id,
            "objectives": objs,
            "workflow": wf_res
        }

    async def create_digital_business(
        self, business_data: Dict[str, Any], user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        name = business_data.get("name", "Nova Startup Digital")
        niche = business_data.get("niche", "Creator Economy")
        audience = business_data.get("audience", "Criadores de conteúdo e profissionais")
        monetization = business_data.get("monetization", "Assinatura mensal recorrente")
        budget = business_data.get("budget", "Bootstrapped")

        description = (
            f"Negócio Digital: {name}\n"
            f"Nicho: {niche} | Público-alvo: {audience}\n"
            f"Monetização: {monetization} | Orçamento: {budget}\n"
            f"Estratégia: Automação completa de workflows com agentes especializados."
        )

        return await self.create_project(
            name=name,
            description=description,
            project_type="business",
            priority="high",
            department="Executive",
            objectives=[
                f"Validar demanda e viabilidade para nicho '{niche}'",
                "Estruturar Business Model Canvas e monetização",
                "Desenvolver MVP da landing page e contratos de API",
                "Aprovar plano de lançamento com o proprietário"
            ],
            auto_start_workflow=True,
            user_id=user_id,
        )

    async def list_projects(
        self,
        status: Optional[str] = None,
        project_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            query = select(ProjectModel)
            if user_id:
                query = query.where(ProjectModel.user_id == user_id)
            if status:
                query = query.where(ProjectModel.status == status)
            if project_type:
                query = query.where(ProjectModel.project_type == project_type)
            result = await session.execute(
                query.order_by(ProjectModel.created_at.desc()).offset(offset).limit(limit)
            )
            projects = result.scalars().all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "project_type": p.project_type,
                    "status": p.status,
                    "priority": p.priority,
                    "department": p.department,
                    "lead_agent_id": p.lead_agent_id,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in projects
            ]

    async def get_project_details(
        self, project_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            project = await session.get(ProjectModel, project_id)
            if not project or (user_id and project.user_id != user_id):
                return None

            tasks_res = await session.execute(select(TaskModel).where(TaskModel.project_id == project_id))
            workflows_res = await session.execute(select(WorkflowModel).where(WorkflowModel.project_id == project_id))
            artifacts_res = await session.execute(select(ArtifactModel).where(ArtifactModel.project_id == project_id))

            return {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "project_type": project.project_type,
                "status": project.status,
                "priority": project.priority,
                "department": project.department,
                "lead_agent_id": project.lead_agent_id,
                "objectives": project.objectives or [],
                "tasks": [
                    {"id": t.id, "title": t.title, "status": t.status, "assigned_agent": t.assigned_agent_id}
                    for t in tasks_res.scalars().all()
                ],
                "workflows": [
                    {"id": w.id, "title": w.title, "status": w.status, "current_node": w.current_node}
                    for w in workflows_res.scalars().all()
                ],
                "artifacts": [
                    {"id": a.id, "name": a.name, "type": a.artifact_type, "path": a.file_path}
                    for a in artifacts_res.scalars().all()
                ]
            }

    async def update_project(
        self, project_id: str, updates: Dict[str, Any], user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            project = await session.get(ProjectModel, project_id)
            if not project or (user_id and project.user_id != user_id):
                return None
            for field in ("name", "description", "status", "priority"):
                if field in updates and updates[field] is not None:
                    setattr(project, field, updates[field])
            await session.commit()
            return {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "priority": project.priority,
            }

    async def delete_project(self, project_id: str, user_id: Optional[str] = None) -> bool:
        async with AsyncSessionLocal() as session:
            project = await session.get(ProjectModel, project_id)
            if not project or (user_id and project.user_id != user_id):
                return False
            await session.delete(project)
            await session.commit()
            return True


project_service = ProjectService()
