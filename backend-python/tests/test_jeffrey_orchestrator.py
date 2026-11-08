import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from src.main import app
from src.services.memory_service import format_memories_prompt
from src.models import AgentMemory
from src.services.jeffrey_orchestrator import call_gemini_generate_content


@pytest.mark.asyncio
async def test_memory_prompt_formatting():
    m1 = AgentMemory(
        id=1,
        user_id=1,
        category="preference",
        key="tom_de_voz",
        content="Prefere respostas concisas e orientadas a números.",
        importance=8,
    )
    m2 = AgentMemory(
        id=2,
        user_id=1,
        category="strategy",
        key="nicho_principal",
        content="Foco em produtos de iluminação e gadgets domésticos.",
        importance=9,
    )
    prompt = format_memories_prompt([m1, m2])
    assert "MEMÓRIAS DE LONGO PRAZO" in prompt
    assert "tom_de_voz" in prompt
    assert "nicho_principal" in prompt


@pytest.mark.asyncio
async def test_gemini_fallback_logic():
    # Mockando httpx client para simular 503 no primeiro modelo e 200 no fallback
    class MockResponse:
        def __init__(self, status_code, data_or_text):
            self.status_code = status_code
            self._data = data_or_text if isinstance(data_or_text, dict) else {}
            self.text = data_or_text if isinstance(data_or_text, str) else ""

        def json(self):
            return self._data

    call_count = 0

    async def mock_post(url, json=None, timeout=None):
        nonlocal call_count
        call_count += 1
        if "gemini-3.8-flash" in url:
            return MockResponse(503, "High demand spike")
        return MockResponse(200, {
            "candidates": [{"content": {"parts": [{"text": "Operação executiva aprovada."}]}}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 50},
        })

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        data, used_model = await call_gemini_generate_content(
            api_key="test-key",
            contents=[{"role": "user", "parts": [{"text": "Teste"}]}],
            system_instruction="Sistema",
            tools_declarations=[],
            preferred_model="gemini-3.8-flash",
        )
        assert used_model == "gemini-3.5-flash-lite"
        assert "candidates" in data
        assert call_count >= 2


@pytest.mark.asyncio
async def test_agent_conversation_and_status_flow():
    rand = uuid.uuid4().hex[:6]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Registro
        reg = await ac.post("/api/auth/register", json={
            "name": f"Jeffrey User {rand}",
            "email": f"jeffrey_{rand}@spirandeli.io",
            "password": "Password123!",
        })
        assert reg.status_code == 201
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Criar conversa
        conv_res = await ac.post("/api/agent/conversations", headers=headers, json={
            "title": "Sessão Estratégica Jeffrey",
            "context_type": "incubator",
        })
        assert conv_res.status_code == 201
        conv_uuid = conv_res.json()["data"]["uuid"]

        # 3. Consultar status do agente
        status_res = await ac.get("/api/agent/status", headers=headers)
        assert status_res.status_code == 200
        assert status_res.json()["agent"]["status"] == "operational"

        # 4. Enviar mensagem interceptada
        mock_gemini_reply = {
            "candidates": [{"content": {"parts": [{"text": "Olá! Sou Jeffrey, seu COO. Como posso ajudar hoje?"}]}}],
            "usageMetadata": {"promptTokenCount": 200, "candidatesTokenCount": 80},
        }

        with patch("src.services.jeffrey_orchestrator.call_gemini_generate_content", return_value=(mock_gemini_reply, "gemini-3.8-flash")):
            msg_res = await ac.post(f"/api/agent/conversations/{conv_uuid}/messages", headers=headers, json={
                "message": "Quais são as diretrizes de hoje?",
            })
            assert msg_res.status_code == 200
            resp_body = msg_res.json()
            assert "data" in resp_body
            assert "Jeffrey" in resp_body["data"]["content"]
            assert len(resp_body["new_messages"]) >= 2

