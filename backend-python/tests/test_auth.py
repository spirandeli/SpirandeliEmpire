import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/up")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_register_and_login_flow():
    rand_suffix = uuid.uuid4().hex[:8]
    email = f"test_{rand_suffix}@spirandeli.io"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Registro
        reg_res = await ac.post(
            "/api/auth/register",
            json={
                "name": "Spira Dev Tester",
                "email": email,
                "password": "StrongPassword123!",
                "device_name": "pytest-runner",
            },
        )
        assert reg_res.status_code == 201, reg_res.text
        reg_data = reg_res.json()
        assert "token" in reg_data
        assert "user" in reg_data
        assert reg_data["user"]["email"] == email
        token = reg_data["token"]

        # 2. Acesso à rota protegida /api/auth/me
        me_res = await ac.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["data"]["email"] == email

        # 3. Atualização de perfil
        profile_res = await ac.put(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"agent_enabled": False},
        )
        assert profile_res.status_code == 200
        assert profile_res.json()["data"]["agent_enabled"] is False

        # 4. Login subsequente
        login_res = await ac.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "StrongPassword123!",
                "device_name": "pytest-login",
            },
        )
        assert login_res.status_code == 200
        assert "token" in login_res.json()


@pytest.mark.asyncio
async def test_unauthenticated_request():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/auth/me")
        assert res.status_code == 401
