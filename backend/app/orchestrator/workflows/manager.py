"""SpirandeliEmpire OS 3.1 — Workflow Manager, Durable Interrupt/Resume & Recovery"""

import json
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import redis
from langgraph.types import Command
from sqlalchemy import select
from app.core.config import settings
from app.orchestrator.state.empire_state import create_initial_state
from app.orchestrator.graphs.jeffrey_supervisor_graph import jeffrey_supervisor_graph
from app.orchestrator.graphs.development_graph import development_graph
from app.orchestrator.graphs.content_graph import content_graph
from app.orchestrator.graphs.clip_graph import clip_graph
from app.orchestrator.graphs.business_graph import business_graph
from app.orchestrator.checkpoints.checkpoint_manager import checkpoint_manager
from app.database.session import AsyncSessionLocal
from app.database.models import (
    WorkflowModel,
    WorkflowExecutionModel,
    ArtifactModel,
    ApprovalModel,
    TaskModel,
)
from app.events.manager import event_system
from app.services.system_service import system_service


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class WorkflowManager:
    def get_graph(self, workflow_type: str):
        if workflow_type == "development":
            return development_graph
        elif workflow_type == "content":
            return content_graph
        elif workflow_type == "clip":
            return clip_graph
        elif workflow_type == "business":
            return business_graph
        return jeffrey_supervisor_graph

    def _is_redis_broker_available(self) -> bool:
        if settings.CELERY_ALWAYS_EAGER:
            return False
        try:
            r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
            return bool(r.ping())
        except Exception:
            return False

    async def _persist_graph_outcome(
        self,
        workflow_id: str,
        execution_id: Optional[str],
        project_id: Optional[str],
        graph,
        config: Dict[str, Any],
        final_state: Dict[str, Any],
        approved_decision: Optional[bool] = None,
    ) -> str:
        """Inspect LangGraph snapshot for interrupts, persist artifacts/approvals, and sync Tasks."""
        snapshot = await graph.aget_state(config)
        is_interrupted = bool(snapshot and snapshot.next)

        interrupt_payloads: List[Dict[str, Any]] = []
        if is_interrupted and snapshot.tasks:
            for t in snapshot.tasks:
                for intr in getattr(t, "interrupts", []) or []:
                    if isinstance(intr.value, dict):
                        interrupt_payloads.append(intr.value)

        if is_interrupted:
            new_status = "waiting_approval"
        elif approved_decision is False or (final_state.get("final_result") or {}).get("status") == "rejected":
            new_status = "rejected"
        elif final_state.get("failed_tasks"):
            new_status = "failed"
        else:
            new_status = "completed"

        async with AsyncSessionLocal() as session:
            wf_record = await session.get(WorkflowModel, workflow_id)
            if wf_record:
                if wf_record.status == "cancelled":
                    return "cancelled"
                wf_record.status = new_status
                wf_record.current_node = final_state.get("current_node", wf_record.current_node)
                sanitized_state = json.loads(
                    json.dumps({k: v for k, v in final_state.items() if k != "__interrupt__"}, default=str)
                )
                wf_record.graph_state = sanitized_state
                wf_record.quality_results = final_state.get("quality_results", [])
                wf_record.checkpoints = checkpoint_manager.get_checkpoints(workflow_id)
                if final_state.get("errors"):
                    wf_record.errors = list(final_state.get("errors", []))

                # Persist newly created artifacts (avoid duplicates by file_path)
                existing_arts = await session.execute(
                    select(ArtifactModel.file_path).where(ArtifactModel.workflow_id == workflow_id)
                )
                existing_paths = set(existing_arts.scalars().all())
                for art in final_state.get("artifacts", []):
                    path_val = art.get("path", "")
                    if path_val and path_val not in existing_paths:
                        existing_paths.add(path_val)
                        session.add(
                            ArtifactModel(
                                user_id=wf_record.user_id,
                                name=art.get("name", "Artefato"),
                                artifact_type=art.get("type", "document"),
                                file_path=path_val,
                                project_id=project_id,
                                workflow_id=workflow_id,
                                creator_agent_id=art.get("creator", "jeffrey"),
                            )
                        )

                # Persist interrupt approvals
                for app_item in interrupt_payloads:
                    app_id = app_item.get("id", str(uuid.uuid4()))
                    existing_app = await session.get(ApprovalModel, app_id)
                    if not existing_app:
                        session.add(
                            ApprovalModel(
                                id=app_id,
                                user_id=wf_record.user_id,
                                workflow_id=workflow_id,
                                project_id=project_id,
                                requested_by_agent_id=app_item.get("requested_by", "jeffrey").lower(),
                                action_name=app_item.get("action_name", "Ação"),
                                description=app_item.get("description", ""),
                                risks=app_item.get("risks", []),
                                status="pending",
                            )
                        )

                # Ensure TaskModel consistency when workflow fails or is rejected
                if new_status in ("failed", "rejected", "cancelled"):
                    t_res = await session.execute(
                        select(TaskModel).where(
                            TaskModel.workflow_id == workflow_id,
                            TaskModel.status.in_(["pending", "in_progress"]),
                        )
                    )
                    for t_row in t_res.scalars().all():
                        t_row.status = "failed" if new_status == "failed" else "cancelled"

            if execution_id:
                exec_rec = await session.get(WorkflowExecutionModel, execution_id)
                if exec_rec:
                    exec_rec.status = new_status
                    if not is_interrupted:
                        exec_rec.finished_at = _utc_now()

            await session.commit()

        for app_item in interrupt_payloads:
            await event_system.publish(
                event_type="AgentWaitingApproval",
                payload=app_item,
                agent_id="jeffrey",
                workflow_id=workflow_id,
                project_id=project_id,
            )

        return new_status

    async def start_workflow(
        self,
        user_request: str,
        workflow_type: str = "supervisor",
        project_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        async_dispatch: bool = True,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        workflow_id = str(uuid.uuid4())
        execution_id = str(uuid.uuid4())
        ctx = dict(context or {})
        if user_id:
            ctx["user_id"] = user_id
        initial_state = create_initial_state(
            workflow_id=workflow_id,
            user_request=user_request,
            project_id=project_id,
            workflow_type=workflow_type,
            context=ctx,
        )

        async with AsyncSessionLocal() as session:
            db_wf = WorkflowModel(
                id=workflow_id,
                user_id=user_id,
                project_id=project_id,
                title=f"Workflow: {user_request[:50]}...",
                workflow_type=workflow_type,
                status="queued" if async_dispatch else "running",
                current_node="start",
                graph_state=initial_state,
                initiated_by=user_id or "user",
            )
            db_exec = WorkflowExecutionModel(
                id=execution_id,
                workflow_id=workflow_id,
                status="queued" if async_dispatch else "running",
                attempt=1,
            )
            session.add(db_wf)
            session.add(db_exec)
            await session.commit()

        await event_system.publish(
            event_type="WorkflowStarted",
            payload={"workflow_id": workflow_id, "title": db_wf.title, "type": workflow_type},
            workflow_id=workflow_id,
            project_id=project_id,
        )

        if async_dispatch and self._is_redis_broker_available():
            from app.workers.celery_app import execute_workflow_task
            task = execute_workflow_task.delay(
                workflow_id=workflow_id,
                execution_id=execution_id,
                user_request=user_request,
                workflow_type=workflow_type,
                project_id=project_id,
                context=context,
            )
            async with AsyncSessionLocal() as session:
                exec_rec = await session.get(WorkflowExecutionModel, execution_id)
                if exec_rec:
                    exec_rec.celery_task_id = task.id
                    await session.commit()

            return {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "celery_task_id": task.id,
                "status": "queued",
            }

        return await self.run_workflow_execution(
            workflow_id=workflow_id,
            execution_id=execution_id,
            user_request=user_request,
            workflow_type=workflow_type,
            project_id=project_id,
            context=context,
        )

    async def run_workflow_execution(
        self,
        workflow_id: str,
        execution_id: str,
        user_request: str,
        workflow_type: str = "supervisor",
        project_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            wf_record = await session.get(WorkflowModel, workflow_id)
            if not wf_record or wf_record.status == "cancelled":
                return {"workflow_id": workflow_id, "status": "cancelled"}
            wf_record.status = "running"
            initial_state = wf_record.graph_state or create_initial_state(
                workflow_id=workflow_id,
                user_request=user_request,
                project_id=project_id,
                workflow_type=workflow_type,
                context=context,
            )
            exec_rec = await session.get(WorkflowExecutionModel, execution_id)
            if exec_rec:
                exec_rec.status = "running"
                exec_rec.started_at = _utc_now()
            await session.commit()

        graph = self.get_graph(workflow_type)
        config = {"configurable": {"thread_id": workflow_id}}

        try:
            final_state = await graph.ainvoke(initial_state, config=config)
            new_status = await self._persist_graph_outcome(
                workflow_id=workflow_id,
                execution_id=execution_id,
                project_id=project_id,
                graph=graph,
                config=config,
                final_state=final_state,
            )
            return {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "status": new_status,
                "final_state": final_state,
            }

        except Exception as e:
            error_msg = str(e)
            await system_service.write_log(
                level="ERROR",
                source="workflow_manager",
                message=f"Workflow {workflow_id} failed: {error_msg}",
                workflow_id=workflow_id,
            )
            async with AsyncSessionLocal() as session:
                wf_record = await session.get(WorkflowModel, workflow_id)
                if wf_record:
                    wf_record.status = "failed"
                    wf_record.errors = [error_msg]
                t_res = await session.execute(
                    select(TaskModel).where(
                        TaskModel.workflow_id == workflow_id,
                        TaskModel.status.in_(["pending", "in_progress"]),
                    )
                )
                for t_row in t_res.scalars().all():
                    t_row.status = "failed"
                exec_rec = await session.get(WorkflowExecutionModel, execution_id)
                if exec_rec:
                    exec_rec.status = "failed"
                    exec_rec.error_message = error_msg
                    exec_rec.finished_at = _utc_now()
                await session.commit()

            await event_system.publish(
                event_type="WorkflowFailed",
                payload={"workflow_id": workflow_id, "error": error_msg},
                workflow_id=workflow_id,
                project_id=project_id,
            )
            return {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "status": "failed",
                "error": error_msg,
            }

    async def resume_workflow(
        self,
        workflow_id: str,
        approved: bool,
        feedback: Optional[str] = None,
        async_dispatch: bool = True,
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            wf_record = await session.get(WorkflowModel, workflow_id)
            if not wf_record:
                raise ValueError("Workflow not found")
            wf_record.status = "running"
            await session.commit()

        if async_dispatch and self._is_redis_broker_available():
            from app.workers.celery_app import resume_workflow_task
            task = resume_workflow_task.delay(
                workflow_id=workflow_id,
                approved=approved,
                feedback=feedback,
            )
            return {
                "workflow_id": workflow_id,
                "celery_task_id": task.id,
                "status": "resumed",
            }
        elif async_dispatch:
            asyncio.create_task(
                self.run_resume_execution(workflow_id, approved, feedback)
            )
            return {
                "workflow_id": workflow_id,
                "status": "resumed",
            }

        return await self.run_resume_execution(workflow_id, approved, feedback)

    async def run_resume_execution(
        self,
        workflow_id: str,
        approved: bool,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            wf_record = await session.get(WorkflowModel, workflow_id)
            if not wf_record:
                raise ValueError("Workflow not found")

            wf_record.status = "running"
            wf_type = wf_record.workflow_type
            project_id = wf_record.project_id
            current_state = dict(wf_record.graph_state or {})
            await session.commit()

        await event_system.publish(
            event_type="WorkflowResumed",
            payload={"workflow_id": workflow_id, "approved": approved, "feedback": feedback},
            workflow_id=workflow_id,
        )

        graph = self.get_graph(wf_type)
        config = {"configurable": {"thread_id": workflow_id}}

        try:
            snapshot = await graph.aget_state(config)
            if snapshot and snapshot.next:
                # Resume paused LangGraph from exact interrupt point
                final_state = await graph.ainvoke(
                    Command(resume={"approved": approved, "feedback": feedback}),
                    config=config,
                )
            else:
                current_state["waiting_for_approval"] = False
                current_state["approval_decision"] = {"approved": approved, "feedback": feedback}
                final_state = await graph.ainvoke(current_state, config=config)

            new_status = await self._persist_graph_outcome(
                workflow_id=workflow_id,
                execution_id=None,
                project_id=project_id,
                graph=graph,
                config=config,
                final_state=final_state,
                approved_decision=approved,
            )
            return {"workflow_id": workflow_id, "status": new_status, "final_state": final_state}
        except Exception as e:
            return {"workflow_id": workflow_id, "status": "failed", "error": str(e)}

    async def cancel_workflow(self, workflow_id: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            wf_record = await session.get(WorkflowModel, workflow_id)
            if not wf_record:
                raise ValueError("Workflow not found")
            if wf_record.status in ["completed", "cancelled", "rejected"]:
                return {"workflow_id": workflow_id, "status": wf_record.status}

            wf_record.status = "cancelled"
            t_res = await session.execute(
                select(TaskModel).where(
                    TaskModel.workflow_id == workflow_id,
                    TaskModel.status.in_(["pending", "in_progress"]),
                )
            )
            for t_row in t_res.scalars().all():
                t_row.status = "cancelled"

            res = await session.execute(
                select(WorkflowExecutionModel).where(
                    WorkflowExecutionModel.workflow_id == workflow_id,
                    WorkflowExecutionModel.status.in_(["queued", "running", "waiting_approval"]),
                )
            )
            for ex in res.scalars().all():
                if ex.celery_task_id:
                    try:
                        from app.workers.celery_app import celery_app
                        celery_app.control.revoke(ex.celery_task_id, terminate=False)
                    except Exception:
                        pass
                ex.status = "cancelled"
                ex.finished_at = _utc_now()
            await session.commit()

        await event_system.publish(
            event_type="WorkflowCancelled",
            payload={"workflow_id": workflow_id},
            workflow_id=workflow_id,
        )
        return {"workflow_id": workflow_id, "status": "cancelled"}

    async def recover_stuck_workflows(self, max_age_minutes: int = 30) -> int:
        cutoff = _utc_now() - timedelta(minutes=max_age_minutes)
        recovered = 0
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(WorkflowModel).where(
                    WorkflowModel.status.in_(["running", "queued"]),
                    WorkflowModel.updated_at < cutoff,
                )
            )
            for wf in res.scalars().all():
                wf.status = "failed"
                wf.errors = list(wf.errors or []) + ["Recovered from stale/stuck worker state."]
                recovered += 1
            await session.commit()
        return recovered


workflow_manager = WorkflowManager()
