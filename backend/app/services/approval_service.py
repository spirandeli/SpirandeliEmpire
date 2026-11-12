"""SpirandeliEmpire OS 3.1 — Human-in-the-Loop Approval Service"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import ApprovalModel
from app.orchestrator.workflows.manager import workflow_manager
from app.events.manager import event_system


class ApprovalService:
    async def list_approvals(
        self, status: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            query = select(ApprovalModel)
            if user_id:
                query = query.where(ApprovalModel.user_id == user_id)
            if status:
                query = query.where(ApprovalModel.status == status)
            result = await session.execute(query.order_by(ApprovalModel.created_at.desc()))
            approvals = result.scalars().all()
            return [
                {
                    "id": a.id,
                    "workflow_id": a.workflow_id,
                    "project_id": a.project_id,
                    "task_id": a.task_id,
                    "requested_by": a.requested_by_agent_id,
                    "action_name": a.action_name,
                    "description": a.description,
                    "resources_used": a.resources_used or {},
                    "risks": a.risks or [],
                    "consequences": a.consequences,
                    "status": a.status,
                    "reviewer_feedback": a.reviewer_feedback,
                    "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in approvals
            ]

    async def decide_approval(
        self,
        approval_id: str,
        approved: bool,
        feedback: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            app = await session.get(ApprovalModel, approval_id)
            if not app or (user_id and app.user_id and app.user_id != user_id):
                raise ValueError("Approval request not found")
            
            app.status = "approved" if approved else "rejected"
            app.reviewer_feedback = feedback
            app.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.commit()
            
            workflow_id = app.workflow_id

        # Resume LangGraph workflow if associated
        wf_result = None
        if workflow_id:
            wf_result = await workflow_manager.resume_workflow(
                workflow_id=workflow_id,
                approved=approved,
                feedback=feedback
            )

        return {
            "id": approval_id,
            "status": "approved" if approved else "rejected",
            "workflow_id": workflow_id,
            "workflow_result": wf_result
        }


approval_service = ApprovalService()

