"""SpirandeliEmpire OS 3.1 — Tests for LangGraph Workflows & Checkpoints"""

import pytest
from app.orchestrator.workflows.manager import workflow_manager
from app.orchestrator.checkpoints.checkpoint_manager import checkpoint_manager


@pytest.mark.asyncio
async def test_supervisor_workflow_execution():
    res = await workflow_manager.start_workflow(
        user_request="Jeffrey, produza 3 Shorts sobre histórias bíblicas sombrias.",
        workflow_type="content",
        async_dispatch=False,
    )
    assert res is not None
    assert "workflow_id" in res
    assert res["status"] in ["completed", "waiting_approval"]

    # Verify checkpoints were persisted
    checkpoints = checkpoint_manager.get_checkpoints(res["workflow_id"])
    assert len(checkpoints) >= 1


@pytest.mark.asyncio
async def test_workflow_async_celery_dispatch():
    res = await workflow_manager.start_workflow(
        user_request="Jeffrey, valide dispatch assíncrono via Celery.",
        workflow_type="content",
        async_dispatch=True,
    )
    assert res is not None
    assert "workflow_id" in res
    assert res["status"] in ["queued", "completed", "waiting_approval"]
