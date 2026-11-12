"""SpirandeliEmpire OS 3.1 — LangGraph, Durability, Human-in-the-Loop & 14 Agents Tests"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.core.config import settings
from app.agents.registry import OFFICIAL_AGENTS
from app.agents.executor import agent_executor
from app.providers.gemini_provider import gemini_provider
from app.orchestrator.checkpoints.persistent_saver import PersistentCheckpointSaver
from app.orchestrator.workflows.manager import workflow_manager
from app.services.approval_service import approval_service
from app.database.session import AsyncSessionLocal
from app.database.models import AgentModel, ApprovalModel, TaskModel, WorkflowModel


@pytest.fixture(autouse=True)
def inject_deterministic_test_llm():
    """Use an explicit test-provider handler so tests don't depend on external Gemini quota."""
    async def _handler(prompt: str, system_instruction: str | None, model: str) -> str:
        return f"[TEST-LLM:{model}] Executed: {prompt[:120]}"

    gemini_provider.set_test_handler(_handler)
    yield
    gemini_provider.set_test_handler(None)


@pytest.mark.asyncio
async def test_all_14_agents_execute_individually():
    assert len(OFFICIAL_AGENTS) == 14
    ids = {a.id for a in OFFICIAL_AGENTS}
    assert len(ids) == 14  # No duplicates

    for defn in OFFICIAL_AGENTS:
        res = await agent_executor.execute_task(
            agent_id=defn.id,
            task_title=f"Teste individual {defn.name}",
            task_description=f"Validar execução do agente {defn.id} ({defn.role})",
        )
        assert res.status == "completed", f"Agent {defn.id} failed: {res.error}"
        assert res.provider == "test-provider"
        assert res.model == defn.model
        assert res.tokens_used > 0

        async with AsyncSessionLocal() as session:
            t = await session.get(TaskModel, res.task_id)
            assert t is not None and t.status == "completed"
            a = await session.get(AgentModel, defn.id)
            assert a is not None and a.operational_state == "idle"
            assert int((a.metrics or {}).get("tasks_completed", 0)) >= 1


@pytest.mark.asyncio
async def test_parallel_delegation_and_dependency_sharing():
    custom_tasks = [
        {"id": "p1", "title": "Pesquisa Independente A", "assigned_agent": "news_agent", "dependencies": [], "status": "pending"},
        {"id": "p2", "title": "Arquitetura Independente B", "assigned_agent": "noe", "dependencies": [], "status": "pending"},
        {"id": "p3", "title": "Consolidação Dependente", "assigned_agent": "balsini", "dependencies": ["p1", "p2"], "status": "pending"},
    ]
    res = await workflow_manager.start_workflow(
        user_request="Executar fluxo paralelo com dependência",
        workflow_type="supervisor",
        context={"custom_tasks": custom_tasks},
        async_dispatch=False,
    )
    assert res["status"] == "completed"
    final_state = res["final_state"]
    assert len(final_state["completed_tasks"]) == 3
    assert final_state["failed_tasks"] == []


@pytest.mark.asyncio
async def test_agent_failure_and_substitution():
    # Force an LLM error on the first call (balsini), then succeed on backup (noe)
    call_count = {"n": 0}

    async def _flaky_handler(prompt: str, system_instruction: str | None, model: str) -> str:
        call_count["n"] += 1
        if "Balsini" in (system_instruction or "") and call_count["n"] <= 2:
            raise RuntimeError("Simulated specialist crash")
        return f"[TEST-LLM] Recovered output for: {prompt[:80]}"

    gemini_provider.set_test_handler(_flaky_handler)

    custom_tasks = [
        {"id": "f1", "title": "Implementar Endpoint Crítico", "assigned_agent": "balsini", "dependencies": [], "status": "pending"},
    ]
    res = await workflow_manager.start_workflow(
        user_request="Testar substituição automática de agente",
        workflow_type="supervisor",
        context={"custom_tasks": custom_tasks},
        async_dispatch=False,
    )
    assert res["status"] == "completed"
    completed = res["final_state"]["completed_tasks"]
    assert len(completed) == 1
    assert completed[0].get("substituted_by") == "noe"


@pytest.mark.asyncio
async def test_durability_interrupt_restart_and_human_approval():
    # 1. Start development workflow -> pauses at deployment_approval via real interrupt()
    res = await workflow_manager.start_workflow(
        user_request="Criar módulo de faturamento",
        workflow_type="development",
        async_dispatch=False,
    )
    wf_id = res["workflow_id"]
    assert res["status"] == "waiting_approval"

    # 2. Simulate process restart: a fresh PersistentCheckpointSaver reads from disk
    fresh_saver = PersistentCheckpointSaver()
    ckpt_tuple = fresh_saver.get_tuple({"configurable": {"thread_id": wf_id, "checkpoint_ns": ""}})
    assert ckpt_tuple is not None

    # 3. Verify ApprovalModel was persisted in DB
    async with AsyncSessionLocal() as session:
        app_res = await session.execute(
            select(ApprovalModel).where(ApprovalModel.workflow_id == wf_id)
        )
        approval = app_res.scalar_one_or_none()
        assert approval is not None
        assert approval.status == "pending"
        approval_id = approval.id

    # 4. Approve with comment -> resumes LangGraph and completes
    decision_res = await approval_service.decide_approval(
        approval_id=approval_id,
        approved=True,
        feedback="Aprovado com comentário de auditoria.",
    )
    assert decision_res["status"] == "approved"
    assert decision_res["workflow_result"]["status"] == "completed"

    async with AsyncSessionLocal() as session:
        wf = await session.get(WorkflowModel, wf_id)
        assert wf is not None and wf.status == "completed"


@pytest.mark.asyncio
async def test_human_in_the_loop_rejection_and_rbac():
    # Start development workflow -> pauses at interrupt()
    res = await workflow_manager.start_workflow(
        user_request="Deploy arriscado para rejeição",
        workflow_type="development",
        async_dispatch=False,
    )
    wf_id = res["workflow_id"]
    assert res["status"] == "waiting_approval"

    async with AsyncSessionLocal() as session:
        app_res = await session.execute(
            select(ApprovalModel).where(ApprovalModel.workflow_id == wf_id)
        )
        approval = app_res.scalar_one()
        approval_id = approval.id

    # Reject via API as owner
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
        dec_res = await client.post(
            f"/api/v1/approvals/{approval_id}/decide",
            json={"approved": False, "feedback": "Risco operacional elevado"},
            headers=headers,
        )
        assert dec_res.status_code == 200
        assert dec_res.json()["status"] == "rejected"
        assert dec_res.json()["workflow_result"]["status"] == "rejected"

