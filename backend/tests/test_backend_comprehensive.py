"""SpirandeliEmpire OS 3.1 — Comprehensive Backend, Auth, DB, Worker & Contract Tests"""

import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import UserModel, ArtifactModel
from app.auth.security import hash_password, create_access_token
from app.memory.service import memory_service
from app.services.system_service import system_service
from app.orchestrator.workflows.manager import workflow_manager


async def _login_owner(client: AsyncClient) -> dict:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_auth_unauthenticated_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ("/api/v1/agents/", "/api/v1/projects/", "/api/v1/integrations/", "/api/v1/tasks/"):
            res = await client.get(path)
            assert res.status_code == 401


@pytest.mark.asyncio
async def test_auth_invalid_login_and_me():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        bad = await client.post("/api/v1/auth/login", json={"username": "owner", "password": "wrong"})
        assert bad.status_code == 401

        headers = await _login_owner(client)
        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["role"] == "owner"


@pytest.mark.asyncio
async def test_rbac_viewer_cannot_write_or_access_admin_mutations():
    viewer_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        session.add(
            UserModel(
                id=viewer_id,
                username=f"viewer_{viewer_id[:8]}",
                email=f"viewer_{viewer_id[:8]}@test.local",
                password_hash=hash_password("viewerpass123"),
                role="viewer",
                is_active=True,
            )
        )
        await session.commit()

    viewer_token = create_access_token(subject=viewer_id, role="viewer")
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Viewer can read
        r_get = await client.get("/api/v1/agents/", headers=viewer_headers)
        assert r_get.status_code == 200

        # Viewer cannot mutate
        r_post = await client.post(
            "/api/v1/tasks/",
            json={"title": "Blocked task"},
            headers=viewer_headers,
        )
        assert r_post.status_code == 403

        r_integ = await client.post(
            "/api/v1/integrations/gemini/test",
            headers=viewer_headers,
        )
        assert r_integ.status_code == 403


@pytest.mark.asyncio
async def test_tasks_and_projects_crud_and_404s():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _login_owner(client)

        # Create project without auto_start_workflow
        p_res = await client.post(
            "/api/v1/projects/",
            json={
                "name": "Audit Test Project",
                "description": "Testing DB persistence",
                "auto_start_workflow": False,
            },
            headers=headers,
        )
        assert p_res.status_code == 201
        project_id = p_res.json()["id"]

        # Create task
        t_res = await client.post(
            "/api/v1/tasks/",
            json={"title": "Verify DB FK", "project_id": project_id, "assigned_agent_id": "ford"},
            headers=headers,
        )
        assert t_res.status_code == 201
        task_id = t_res.json()["id"]

        # Update task status
        u_res = await client.patch(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": "completed", "result_summary": "Verified"},
            headers=headers,
        )
        assert u_res.status_code == 200

        # Delete task & project
        d_task = await client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
        assert d_task.status_code == 204
        d_proj = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
        assert d_proj.status_code == 204

        # 404 checks (no 500s)
        assert (await client.get("/api/v1/projects/nonexistent", headers=headers)).status_code == 404
        assert (await client.post("/api/v1/workflows/nonexistent/resume", json={"approved": True}, headers=headers)).status_code == 404
        assert (await client.post("/api/v1/approvals/nonexistent/decide", json={"approved": True}, headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_memory_and_system_logs_settings_persistence():
    mem = await memory_service.store_memory(
        agent_id="jeffrey",
        key="test_policy",
        content="Always run pytest before release.",
        memory_type="long_term",
    )
    assert mem["key"] == "test_policy"
    items = await memory_service.list_memories(agent_id="jeffrey")
    assert any(m["key"] == "test_policy" for m in items)

    await system_service.write_log("INFO", "test_suite", "Log persistence check")
    logs = await system_service.list_logs(level="INFO", limit=10)
    assert any("Log persistence check" in l["message"] for l in logs)

    setting = await system_service.upsert_setting("audit_mode", {"enabled": True}, "Audit flag")
    assert setting["value"]["enabled"] is True


@pytest.mark.asyncio
async def test_artifact_download_blocks_outside_storage():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _login_owner(client)
        me_res = await client.get("/api/v1/auth/me", headers=headers)
        owner_id = me_res.json()["id"]

        art_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as session:
            session.add(
                ArtifactModel(
                    id=art_id,
                    user_id=owner_id,
                    name="Evil Artifact",
                    artifact_type="document",
                    file_path="/etc/passwd",
                    creator_agent_id="jeffrey",
                )
            )
            await session.commit()

        res = await client.get(f"/api/v1/artifacts/{art_id}/download", headers=headers)
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_workflow_inline_and_cancel():
    res = await workflow_manager.start_workflow(
        user_request="Teste de cancelamento e execução",
        workflow_type="development",
        async_dispatch=False,
    )
    wf_id = res["workflow_id"]
    assert res["status"] in ("completed", "waiting_approval")

    # Cancelling a waiting_approval workflow transitions it to cancelled; completed stays completed
    cancel_res = await workflow_manager.cancel_workflow(wf_id)
    expected = "completed" if res["status"] == "completed" else "cancelled"
    assert cancel_res["status"] == expected
