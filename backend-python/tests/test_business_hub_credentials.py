import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.future import select

from src.main import app
from src.models import Business
from src.services.business_credentials import get_platform_credentials
from tests.conftest import TestingSessionLocal


async def _register(ac: AsyncClient) -> dict:
    rand = uuid.uuid4().hex[:8]
    reg = await ac.post("/api/auth/register", json={
        "name": f"Owner {rand}",
        "email": f"owner_{rand}@spirandeli.io",
        "password": "Password123!",
    })
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['token']}"}


@pytest.mark.asyncio
async def test_business_hub_detail_and_channel_credentials_vault():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = await _register(ac)

        res = await ac.post("/api/businesses", json={
            "name": "Canal Dark Credenciais",
            "archetype": "canal_dark",
            "niche": "Mistérios",
        }, headers=headers)
        assert res.status_code == 201, res.text
        biz_id = res.json()["data"]["id"]

        # 1. Detalhe traz automações reais (antes vinha vazio -> contador "0")
        detail = (await ac.get(f"/api/businesses/{biz_id}", headers=headers)).json()["data"]
        assert len(detail["automations"]) >= 1
        assert detail["automations"][0]["type"] == "dark_channel_mining"
        assert detail["tiktok_products"] == []
        assert detail["channels"]["youtube"]["configured"] is False
        assert detail["business_model"]

        # 2. Salva acessos do YouTube e TikTok
        save = await ac.put(f"/api/businesses/{biz_id}/credentials", json={
            "youtube": {
                "enabled": True,
                "handle": "@misterios",
                "username_email": "canal@gmail.com",
                "password": "SenhaYT#123",
                "auto_publish": True,
            },
            "tiktok": {
                "enabled": True,
                "handle": "@misterios.tt",
                "username_email": "canal_tt@gmail.com",
                "password": "SenhaTT#456",
                "api_key_or_token": "tt-session-token",
            },
        }, headers=headers)
        assert save.status_code == 200, save.text
        assert set(save.json()["channels_configured"]) == {"youtube", "tiktok"}

        # 3. Segredos ficam cifrados no banco
        async with TestingSessionLocal() as session:
            biz = (await session.execute(select(Business).where(Business.id == biz_id))).scalar_one()
            stored = biz.acquisition_channels
            assert stored["youtube"]["password"] != "SenhaYT#123"
            assert "SenhaYT#123" not in str(stored)
            assert "tt-session-token" not in str(stored)
            # Helper usado pelos workers de integração descriptografa corretamente
            assert get_platform_credentials(biz, "tiktok")["api_key_or_token"] == "tt-session-token"
            assert get_platform_credentials(biz, "instagram") is None

        # 4. Detalhe geral nunca expõe senha
        detail = (await ac.get(f"/api/businesses/{biz_id}", headers=headers)).json()["data"]
        yt = detail["channels"]["youtube"]
        assert yt["has_password"] is True and yt["configured"] is True
        assert "password" not in yt
        assert "SenhaYT#123" not in str(detail)

        # 5. Reveal para o dono retorna em texto puro
        creds = (await ac.get(f"/api/businesses/{biz_id}/credentials", headers=headers)).json()["data"]
        assert creds["youtube"]["password"] == "SenhaYT#123"
        assert creds["tiktok"]["api_key_or_token"] == "tt-session-token"

        # 6. Atualização sem senha mantém a senha; "__clear__" remove o token
        await ac.put(f"/api/businesses/{biz_id}/credentials", json={
            "youtube": {"handle": "@novo_handle", "password": ""},
            "tiktok": {"api_key_or_token": "__clear__"},
        }, headers=headers)
        creds = (await ac.get(f"/api/businesses/{biz_id}/credentials", headers=headers)).json()["data"]
        assert creds["youtube"]["handle"] == "@novo_handle"
        assert creds["youtube"]["password"] == "SenhaYT#123"
        assert creds["tiktok"]["api_key_or_token"] is None
        assert creds["tiktok"]["password"] == "SenhaTT#456"

        # 7. Edição de dados gerais do negócio
        upd = await ac.put(f"/api/businesses/{biz_id}", json={
            "name": "Canal Dark Renomeado",
            "north_star_metric": "monthly_views",
            "brand_rules": {"tone_of_voice": "Sombrio", "target_audience": "Curiosos"},
        }, headers=headers)
        assert upd.status_code == 200, upd.text
        upd_data = upd.json()["data"]
        assert upd_data["name"] == "Canal Dark Renomeado"
        assert upd_data["brand_rules"]["tone_of_voice"] == "Sombrio"
        assert len(upd_data["automations"]) >= 1

        # 8. Listagem traz contadores e canais configurados
        listing = (await ac.get("/api/businesses", headers=headers)).json()["data"]
        item = next(b for b in listing if b["id"] == biz_id)
        assert item["automations_count"] >= 1
        assert set(item["channels_configured"]) == {"youtube", "tiktok"}

        # 9. Outro usuário não acessa as credenciais
        other_headers = await _register(ac)
        denied = await ac.get(f"/api/businesses/{biz_id}/credentials", headers=other_headers)
        assert denied.status_code == 404
        denied_put = await ac.put(
            f"/api/businesses/{biz_id}/credentials",
            json={"youtube": {"password": "hack"}},
            headers=other_headers,
        )
        assert denied_put.status_code == 404

