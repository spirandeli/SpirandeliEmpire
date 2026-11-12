"""SpirandeliEmpire OS 3.1 — Celery Background Worker with Idempotency & Retries"""

import asyncio
from typing import Optional, Dict, Any
from celery import Celery
import redis
from app.core.config import settings

celery_app = Celery(
    "spirandeliempire_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=1500,
    task_time_limit=1800,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    task_always_eager=settings.CELERY_ALWAYS_EAGER,
)


def _run_async_in_worker(coro):
    """Run async coroutine in Celery worker and dispose SQLAlchemy pool before loop closes."""
    async def _wrapper():
        from app.database.session import engine
        try:
            return await coro
        finally:
            await engine.dispose()

    return asyncio.run(_wrapper())
def _acquire_workflow_lock(workflow_id: str, ttl_seconds: int = 1800) -> bool:
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        return bool(r.set(f"workflow_lock:{workflow_id}", "locked", nx=True, ex=ttl_seconds))
    except Exception:
        # If Redis is unreachable in eager/unit-test mode, allow execution
        return True


def _release_workflow_lock(workflow_id: str) -> None:
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.delete(f"workflow_lock:{workflow_id}")
    except Exception:
        pass


@celery_app.task(
    bind=True,
    name="tasks.execute_workflow",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=2,
)
def execute_workflow_task(
    self,
    workflow_id: str,
    execution_id: str,
    user_request: str,
    workflow_type: str = "supervisor",
    project_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute LangGraph workflow asynchronously inside Celery worker."""
    if not _acquire_workflow_lock(workflow_id):
        return {"workflow_id": workflow_id, "status": "duplicate_skipped"}

    try:
        import json
        from app.orchestrator.workflows.manager import workflow_manager
        res = _run_async_in_worker(
            workflow_manager.run_workflow_execution(
                workflow_id=workflow_id,
                execution_id=execution_id,
                user_request=user_request,
                workflow_type=workflow_type,
                project_id=project_id,
                context=context,
            )
        )
        return json.loads(json.dumps(res, default=str))
    finally:
        _release_workflow_lock(workflow_id)


@celery_app.task(
    bind=True,
    name="tasks.resume_workflow",
    max_retries=2,
    retry_backoff=True,
)
def resume_workflow_task(
    self,
    workflow_id: str,
    approved: bool,
    feedback: Optional[str] = None,
) -> Dict[str, Any]:
    """Resume paused LangGraph workflow in Celery worker."""
    if not _acquire_workflow_lock(workflow_id):
        return {"workflow_id": workflow_id, "status": "duplicate_skipped"}

    try:
        import json
        from app.orchestrator.workflows.manager import workflow_manager
        res = _run_async_in_worker(
            workflow_manager.run_resume_execution(
                workflow_id=workflow_id,
                approved=approved,
                feedback=feedback,
            )
        )
        return json.loads(json.dumps(res, default=str))
    finally:
        _release_workflow_lock(workflow_id)
