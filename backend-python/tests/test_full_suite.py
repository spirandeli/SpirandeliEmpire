import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_full_system_flow():
    rand = uuid.uuid4().hex[:8]
    email = f"emp_{rand}@spirandeli.io"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Registro e Bearer Token
        reg = await ac.post("/api/auth/register", json={
            "name": f"Tester {rand}",
            "email": email,
            "password": "Password123!",
        })
        assert reg.status_code == 201, reg.text
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Listagem de Negócios (já deve ter o do starter kit!)
        biz_res = await ac.get("/api/businesses", headers=headers)
        assert biz_res.status_code == 200
        businesses = biz_res.json()["data"]
        assert len(businesses) >= 1
        biz_id = businesses[0]["id"]

        # 3. Criar nova tarefa Kanban
        task_res = await ac.post("/api/tasks", headers=headers, json={
            "business_id": biz_id,
            "title": "Configurar campanha no TikTok Ads",
            "priority": "high",
            "assignee": "user",
        })
        assert task_res.status_code == 201
        task_id = task_res.json()["data"]["id"]

        # 4. Mover tarefa no Kanban
        move_res = await ac.patch(f"/api/tasks/{task_id}/move", headers=headers, json={
            "status": "done",
            "position": 1,
        })
        assert move_res.status_code == 200
        assert move_res.json()["data"]["status"] == "done"

        # 5. Quadro Kanban
        board_res = await ac.get("/api/tasks/board", headers=headers)
        assert board_res.status_code == 200
        columns = board_res.json()["data"]
        assert len(columns) == 5

        # 6. Fila de Supervisão (Summary e Lista)
        appr_sum = await ac.get("/api/approvals/summary", headers=headers)
        assert appr_sum.status_code == 200
        assert "total_awaiting" in appr_sum.json()["data"]

        appr_list = await ac.get("/api/approvals", headers=headers)
        assert appr_list.status_code == 200
        approvals = appr_list.json()["data"]
        if len(approvals) > 0:
            appr_id = approvals[0]["id"]
            # Aprovação com hook
            approve_res = await ac.post(f"/api/approvals/{appr_id}/approve", headers=headers, json={
                "selected_hook_index": 0,
            })
            assert approve_res.status_code == 200
            assert approve_res.json()["data"]["status"] == "approved"

        # 7. Conversas com Agente
        conv_res = await ac.get("/api/agent/conversations", headers=headers)
        assert conv_res.status_code == 200
        convs = conv_res.json()["data"]
        assert len(convs) >= 1
        conv_uuid = convs[0]["uuid"]

        # 8. Logs do Agente
        logs_res = await ac.get("/api/agent/logs", headers=headers)
        assert logs_res.status_code == 200
        assert "data" in logs_res.json()

        # 9. Feed de Calendário RFC 5545
        feed_info = await ac.get("/api/v1/calendar/me/feed-url", headers=headers)
        assert feed_info.status_code == 200
        cal_token = feed_info.json()["calendar_token"]

        ics_res = await ac.get(f"/api/v1/calendar/feed/{cal_token}.ics")
        assert ics_res.status_code == 200
        assert "BEGIN:VCALENDAR" in ics_res.text

        # 10. Academia de Idiomas
        lang_res = await ac.get("/api/languages/profile", headers=headers)
        assert lang_res.status_code == 200

        new_lang = await ac.post("/api/languages/profile", headers=headers, json={
            "target_language": "Inglês",
            "learning_focus": "business",
            "study_days": [1, 2, 3, 4, 5],
            "preferred_time": "08:00",
        })
        assert new_lang.status_code == 201
        profile_id = new_lang.json()["profile"]["id"]

        vault_word = await ac.post(f"/api/languages/profiles/{profile_id}/vault", headers=headers, json={
            "term_or_phrase": "Scalability",
            "translation": "Escalabilidade",
        })
        assert vault_word.status_code == 201

        # 12. Métricas de Crescimento e Simulação de Webhook
        growth_res = await ac.get(f"/api/businesses/{biz_id}/growth-metrics", headers=headers)
        assert growth_res.status_code == 200
        assert "funnel" in growth_res.json()

        opt_res = await ac.post(f"/api/businesses/{biz_id}/optimize-growth", headers=headers)
        assert opt_res.status_code == 200

        sim_res = await ac.post(f"/api/businesses/{biz_id}/webhooks/simulate", headers=headers, json={
            "event_type": "purchase_approved",
            "gross_amount": 197.00,
        })
        assert sim_res.status_code == 200

        # 13. Automações do Negócio
        autos_res = await ac.get(f"/api/businesses/{biz_id}/automations", headers=headers)
        assert autos_res.status_code == 200
        assert len(autos_res.json()["data"]) >= 1

        # 14. Integrações Google
        google_res = await ac.get("/api/integrations/google/redirect", headers=headers)
        assert google_res.status_code == 200
        assert "url" in google_res.json()

        sync_res = await ac.post("/api/integrations/google/sync", headers=headers)
        assert sync_res.status_code == 200

