import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_admin_governance_and_automations_crud():
    rand = uuid.uuid4().hex[:8]
    email = f"admin_{rand}@spirandeli.io"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Registro de Admin
        reg = await ac.post("/api/auth/register", json={
            "name": f"Admin {rand}",
            "email": email,
            "password": "Password123!",
        })
        assert reg.status_code == 201
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Promover usuário para Admin no DB e testar endpoints administrativos
        from src.database import AsyncSessionLocal
        from src.models import User
        from sqlalchemy.future import select

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.email == email))
            u = res.scalar_one()
            u.is_admin = True
            await session.commit()

        # 3. Estatísticas FinOps Admin
        stats_res = await ac.get("/api/admin/ai-governance/stats", headers=headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert "metrics" in stats
        assert "users" in stats

        # 4. Atualizar Limites de Token
        user_id = reg.json()["user"]["id"]
        limits_res = await ac.patch(
            f"/api/admin/ai-governance/users/{user_id}/limits",
            headers=headers,
            json={"monthly_token_limit": 20000000, "is_ai_active": True},
        )
        assert limits_res.status_code == 200
        assert limits_res.json()["user"]["monthly_token_limit"] == 20000000

        # 5. Toggle Kill-Switch
        ks_res = await ac.post(f"/api/admin/ai-governance/users/{user_id}/kill-switch", headers=headers)
        assert ks_res.status_code == 200
        assert ks_res.json()["is_ai_active"] is False

        # Reativar Kill-Switch
        ks_res2 = await ac.post(f"/api/admin/ai-governance/users/{user_id}/kill-switch", headers=headers)
        assert ks_res2.status_code == 200
        assert ks_res2.json()["is_ai_active"] is True

        # 6. Reset Usage
        reset_res = await ac.post(f"/api/admin/ai-governance/users/{user_id}/reset-usage", headers=headers)
        assert reset_res.status_code == 200
        assert reset_res.json()["tokens_used_this_month"] == 0

        # 7. Automações CRUD
        biz_res = await ac.get("/api/businesses", headers=headers)
        biz_id = biz_res.json()["data"][0]["id"]

        create_auto = await ac.post(
            f"/api/businesses/{biz_id}/automations",
            headers=headers,
            json={
                "type": "custom_sync",
                "name": "Sincronização Customizada",
                "cron_expression": "0 0 * * *",
                "is_enabled": True,
            },
        )
        assert create_auto.status_code == 201
        auto_id = create_auto.json()["data"]["id"]

        # Atualizar automação
        up_auto = await ac.put(
            f"/api/businesses/{biz_id}/automations/{auto_id}",
            headers=headers,
            json={"is_enabled": False, "cron_expression": "0 12 * * *"},
        )
        assert up_auto.status_code == 200
        assert up_auto.json()["data"]["is_enabled"] is False

        # Deletar automação
        del_auto = await ac.delete(
            f"/api/businesses/{biz_id}/automations/{auto_id}",
            headers=headers,
        )
        assert del_auto.status_code == 204

        # 8. Webhook Inbound
        biz_show = await ac.get(f"/api/businesses/{biz_id}", headers=headers)
        secret_token = biz_show.json()["data"]["webhook_secret_token"]

        webhook_res = await ac.post(
            f"/api/webhooks/in/{secret_token}",
            json={
                "event": "purchase_approved",
                "source": "hotmart",
                "amount": 297.00,
            },
        )
        assert webhook_res.status_code == 200
        assert webhook_res.json()["status"] == "success"

