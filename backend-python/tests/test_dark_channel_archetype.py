import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_dark_channel_archetype_and_studio_flow():
    rand = uuid.uuid4().hex[:8]
    email = f"creator_{rand}@spirandeli.io"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Registro de Usuário
        reg = await ac.post("/api/auth/register", json={
            "name": f"Creator {rand}",
            "email": email,
            "password": "Password123!",
        })
        assert reg.status_code == 201, reg.text
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Cria negócio com arquétipo canal_dark
        create_payload = {
            "name": "Mistérios Ocultos do Universo",
            "archetype": "canal_dark",
            "niche": "Astronomia & Mistérios Espaciais",
            "description": "Canal Dark focado em anomalias cósmicas e exploração espacial.",
            "target_kpi_value": 300000.0,
        }
        res = await ac.post("/api/businesses", json=create_payload, headers=headers)
        assert res.status_code == 201, res.text
        biz_data = res.json()["data"]
        assert biz_data["name"] == "Mistérios Ocultos do Universo"
        assert biz_data["archetype"] == "canal_dark"
        assert biz_data["type"] == "dark_channel_automation"
        assert biz_data["north_star_metric"] == "monthly_views"
        assert "value_propositions" in biz_data["canvas"]
        biz_id = biz_data["id"]

        # 3. Testa listagem de pautas mineradas pelo Dark Studio
        res_topics = await ac.get(f"/api/businesses/{biz_id}/dark-studio/topics", headers=headers)
        assert res_topics.status_code == 200
        topics = res_topics.json()["data"]
        assert len(topics) >= 1
        assert "topic" in topics[0]
        assert "predicted_ctr" in topics[0]

        # 4. Testa geração de roteiro Dark com cenas e prompts de IA
        script_payload = {
            "title": "O Sinal WOW! que a NASA Não Consegue Explicar",
            "topic": "O sinal de rádio captado em 1977 que parecia uma transmissão extraterrestre.",
            "format_type": "short",
            "target_platform": "youtube_shorts",
            "tone": "Misterioso e investigativo",
            "visual_style": "Cinematic 8k photorealistic space observatory, retro 70s analog radio telescopes",
            "voice_persona": "Voz grave e hipnótica",
        }
        res_script = await ac.post(
            f"/api/businesses/{biz_id}/dark-studio/generate-script",
            json=script_payload,
            headers=headers,
        )
        assert res_script.status_code == 201, res_script.text
        script_data = res_script.json()["data"]
        assert script_data["business_id"] == biz_id
        assert script_data["title"] == script_payload["title"]
        assert len(script_data["scenes"]) >= 3
        assert script_data["scenes"][0]["visual_prompt"] is not None
        assert script_data["scenes"][0]["narration"] is not None
        assert script_data["approval_queue_id"] is not None

        # 5. Testa listagem de roteiros do Dark Studio
        res_list = await ac.get(f"/api/businesses/{biz_id}/dark-studio/scripts", headers=headers)
        assert res_list.status_code == 200
        scripts = res_list.json()["data"]
        assert len(scripts) >= 1
        assert scripts[0]["title"] == script_payload["title"]
        assert scripts[0]["status"] == "supervision"
