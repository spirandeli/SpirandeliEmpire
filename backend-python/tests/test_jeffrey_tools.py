import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from src.main import app
from src.services.agent_tools.vps_tool import get_vps_telemetry
from src.services.agent_tools.venture_tool import list_user_ventures, create_business_venture
from src.services.agent_tools.task_workflow_tool import create_kanban_task, move_kanban_task, submit_to_approval_queue
from src.services.agent_tools.knowledge_tool import search_knowledge_tool
from src.services.agent_tools import execute_agent_tool, get_gemini_tools_declarations


@pytest.mark.asyncio
async def test_vps_telemetry():
    data = get_vps_telemetry()
    assert "status" in data
    assert "cpu" in data
    assert "percent" in data["cpu"]
    assert "memory" in data
    assert "disk" in data
    assert "uptime" in data


@pytest.mark.asyncio
async def test_tools_declarations():
    declarations = get_gemini_tools_declarations()
    assert len(declarations) >= 8
    names = [d["name"] for d in declarations]
    assert "get_vps_telemetry" in names
    assert "list_docker_containers" in names
    assert "create_business_venture" in names
    assert "create_kanban_task" in names
    assert "submit_to_approval_queue" in names
    assert "search_knowledge_tool" in names


@pytest.mark.asyncio
async def test_venture_and_task_tools_flow(db_session: AsyncSession = None):
    # Test via API client to obtain real user session and token
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register user
        import uuid
        email = f"tool_test_{uuid.uuid4().hex[:6]}@spirandeli.io"
        reg = await ac.post("/api/auth/register", json={
            "name": "Tool Tester",
            "email": email,
            "password": "Password123!",
        })
        assert reg.status_code == 201
        token = reg.json()["token"]
        user_id = reg.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check existing starter kit business
        biz_res = await ac.get("/api/businesses", headers=headers)
        assert biz_res.status_code == 200
        businesses = biz_res.json()["data"]
        biz_id = businesses[0]["id"]

        # 1. Test execute_agent_tool for vps
        vps = await execute_agent_tool("get_vps_telemetry", {}, user_id, None)
        assert "cpu" in vps

        # 2. Test search_knowledge_tool
        rag = await search_knowledge_tool("TikTok Shop")
        assert "found" in rag

        # 3. Test agent status endpoint
        status_res = await ac.get("/api/agent/status", headers=headers)
        assert status_res.status_code == 200
        body = status_res.json()
        assert "agent" in body
        assert body["agent"]["name"] == "Jeffrey"
        assert "knowledge_base" in body
        assert "vps" in body

