"""SpirandeliEmpire OS 3.1 — Tests for FastAPI API Endpoints"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


async def _get_owner_headers(client: AsyncClient) -> dict:
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_api_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("healthy", "degraded")
        assert "3.2.0" in data["version"]
        assert "dependencies" in data


@pytest.mark.asyncio
async def test_api_agents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_owner_headers(client)
        res = await client.get("/api/v1/agents/", headers=headers)
        assert res.status_code == 200
        agents = res.json()
        assert len(agents) == 14

        jeffrey = await client.get("/api/v1/agents/jeffrey", headers=headers)
        assert jeffrey.status_code == 200
        assert jeffrey.json()["name"] == "Jeffrey"


@pytest.mark.asyncio
async def test_api_system_metrics():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_owner_headers(client)
        res = await client.get("/api/v1/system/metrics", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data


@pytest.mark.asyncio
async def test_api_integrations():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _get_owner_headers(client)
        res = await client.get("/api/v1/integrations/", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
