import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


async def _get_auth_token():
    suffix = uuid.uuid4().hex[:8]
    email = f"lang_{suffix}@spirandeli.io"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        reg = await ac.post(
            "/api/auth/register",
            json={
                "name": "Language Tester",
                "email": email,
                "password": "Password123!",
                "device_name": "pytest-lang",
            },
        )
        assert reg.status_code == 201
        return reg.json()["token"]


@pytest.mark.asyncio
async def test_language_onboarding_and_placement_flow():
    token = await _get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        # 1. Perfil inicial: deve indicar has_profile = False
        res = await ac.get("/api/languages/profile")
        assert res.status_code == 200
        assert res.json()["has_profile"] is False

        # 2. Criação do perfil de idiomas
        create_res = await ac.post(
            "/api/languages/profile",
            json={
                "target_language": "Inglês",
                "learning_focus": "business",
                "study_days": [1, 2, 3, 4, 5],
                "preferred_time": "08:00",
                "daily_duration_minutes": 15,
            },
        )
        assert create_res.status_code == 201
        p_data = create_res.json()["profile"]
        profile_id = p_data["id"]
        assert p_data["cefr_level"] == "UNSET"

        # 3. Busca do Teste de Nivelamento
        test_res = await ac.get(f"/api/languages/profiles/{profile_id}/placement-test")
        assert test_res.status_code == 200
        t_data = test_res.json()
        assert "questions" in t_data
        assert "placement_test" in t_data
        questions = t_data["questions"]
        assert len(questions) == 10
        assert questions[0]["target_cefr"] == "A1"
        assert questions[-1]["target_cefr"] == "C1"

        # 4. Submissão do teste respondendo todas as opções corretas
        answers = [
            {"question_id": q["id"], "answer": q["correct_option"]}
            for q in questions
        ]
        sub_res = await ac.post(
            f"/api/languages/profiles/{profile_id}/placement-test",
            json={"answers": answers},
        )
        assert sub_res.status_code == 200
        sub_data = sub_res.json()
        assert sub_data["cefr_level"] == "C1"
        assert sub_data["evaluation"]["score_total"] == 10
        assert len(sub_data["evaluation"]["strengths"]) > 0

        # 5. Validação de perfil atualizado
        prof_after = await ac.get("/api/languages/profile")
        assert prof_after.status_code == 200
        assert prof_after.json()["profile"]["cefr_level"] == "C1"


@pytest.mark.asyncio
async def test_spanish_language_flow():
    """Valida fluxo de ponta a ponta quando o usuário escolhe Espanhol."""
    token = await _get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        # 1. Cria perfil de Espanhol
        create_res = await ac.post(
            "/api/languages/profile",
            json={
                "target_language": "Espanhol",
                "learning_focus": "business",
                "study_days": [1, 2, 3, 4, 5],
                "preferred_time": "07:30",
            },
        )
        assert create_res.status_code == 201
        profile_id = create_res.json()["profile"]["id"]

        # 2. Teste de Nivelamento deve vir em Espanhol
        test_res = await ac.get(f"/api/languages/profiles/{profile_id}/placement-test")
        assert test_res.status_code == 200
        t_data = test_res.json()
        questions = t_data["questions"]
        assert len(questions) == 10
        # Questões em espanhol
        assert any("¿" in q["question"] or "español" in q["question"].lower() for q in questions)

        # 3. Submissão do teste de nivelamento em Espanhol
        answers = [{"question_id": q["id"], "answer": q["correct_option"]} for q in questions]
        sub_test_res = await ac.post(
            f"/api/languages/profiles/{profile_id}/placement-test",
            json={"answers": answers},
        )
        assert sub_test_res.status_code == 200
        assert sub_test_res.json()["cefr_level"] == "C1"
        assert sub_test_res.json()["evaluation"]["score_total"] == 10

        # 4. Busca da Sessão do Dia: Deve vir 100% em Espanhol
        today_res = await ac.get(f"/api/languages/profiles/{profile_id}/today")
        assert today_res.status_code == 200
        session = today_res.json()["session"]
        payload = session["lesson_payload"]

        assert payload["target_language"] == "Espanhol"
        # Bloco 1 com termos em espanhol
        assert payload["block1_srs"]["items"][0]["term"] == "Ponerse al día"
        # Bloco 2 com diálogo em espanhol
        assert "sara" in payload["block2_immersion"]["scenario_text"].lower()
        assert "alejandro" in payload["block2_immersion"]["scenario_text"].lower()
        # Bloco 3 desafio em espanhol
        assert "espanhol" in payload["block3_active_output"]["scenario_prompt"].lower() or "español" in payload["block3_active_output"]["scenario_prompt"].lower()

        # 5. Submissão da sessão em espanhol
        b1_answers = {str(item["id"]): item["correct_option"] for item in payload["block1_srs"]["items"]}
        b2_answers = {str(q["id"]): q["correct_option"] for q in payload["block2_immersion"]["questions"]}

        sub_session_res = await ac.post(
            f"/api/languages/profiles/{profile_id}/sessions/{session['id']}/submit",
            json={
                "user_answers": {
                    "block1_srs": b1_answers,
                    "block2_immersion": b2_answers,
                    "block3_active_output": "Hola Sara, gracias por la actualización. Ya estamos ejecutando las prioridades para mitigar el impacto.",
                },
                "time_spent_seconds": 900,
            },
        )
        assert sub_session_res.status_code == 200
        sub_s_data = sub_session_res.json()
        assert sub_s_data["score"] >= 90
        # Feedback nativo em espanhol
        assert "hola sara" in sub_s_data["evaluation"]["block3_active_evaluation"]["natural_native_version"].lower()

        # 6. Cofre SRS deve conter os termos em espanhol
        vault_res = await ac.get(f"/api/languages/profiles/{profile_id}/vault")
        assert vault_res.status_code == 200
        vault_items = vault_res.json()["items"]
        terms = [item["term_or_phrase"] for item in vault_items]
        assert "Mitigar el impacto" in terms or "Ponerse al día" in terms


@pytest.mark.asyncio
async def test_language_daily_session_and_srs_vault():
    token = await _get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        # Cria perfil
        create_res = await ac.post(
            "/api/languages/profile",
            json={
                "target_language": "Inglês",
                "learning_focus": "business",
                "study_days": [1, 2, 3, 4, 5],
                "preferred_time": "07:30",
            },
        )
        profile_id = create_res.json()["profile"]["id"]

        # Busca sessão diária (Gera 3 blocos)
        today_res = await ac.get(f"/api/languages/profiles/{profile_id}/today")
        assert today_res.status_code == 200
        session = today_res.json()["session"]
        assert session["status"] == "ready"
        payload = session["lesson_payload"]

        # Valida a presença dos 3 blocos exigidos pelo LanguageFocusPlayer
        assert "block1_srs" in payload
        assert "block2_immersion" in payload
        assert "block3_active_output" in payload
        assert len(payload["block1_srs"]["items"]) >= 3
        assert len(payload["block2_immersion"]["questions"]) >= 2
        assert "scenario_prompt" in payload["block3_active_output"]

        # Submete a sessão diária com respostas para todos os itens
        b1_answers = {str(item["id"]): item["correct_option"] for item in payload["block1_srs"]["items"]}
        b2_answers = {str(q["id"]): q["correct_option"] for q in payload["block2_immersion"]["questions"]}

        sub_res = await ac.post(
            f"/api/languages/profiles/{profile_id}/sessions/{session['id']}/submit",
            json={
                "user_answers": {
                    "block1_srs": b1_answers,
                    "block2_immersion": b2_answers,
                    "block3_active_output": "Hi Sarah, thank you for the alignment. We are mitigating the impact by deploying core modules.",
                },
                "time_spent_seconds": 850,
            },
        )
        assert sub_res.status_code == 200
        sub_data = sub_res.json()
        assert sub_data["score"] >= 90
        assert sub_data["streak_days"] >= 1
        assert "block3_active_evaluation" in sub_data["evaluation"]

        # Valida que novos termos foram salvos no cofre SRS
        vault_res = await ac.get(f"/api/languages/profiles/{profile_id}/vault")
        assert vault_res.status_code == 200
        v_data = vault_res.json()
        assert v_data["stats"]["total"] >= 2
        vault_item = v_data["items"][0]
        initial_mastery = vault_item["mastery_level"]

        # Testa a rota de revisão SRS (Relembrado: deve subir maestria)
        rev_res = await ac.post(
            f"/api/languages/profiles/{profile_id}/vault/{vault_item['id']}/review",
            json={"remembered": True},
        )
        assert rev_res.status_code == 200
        updated_item = rev_res.json()["item"]
        assert updated_item["mastery_level"] == initial_mastery + 1


@pytest.mark.asyncio
async def test_placement_test_options_are_shuffled():
    """Valida que as opções de resposta no teste de nivelamento são embaralhadas aleatoriamente."""
    token = await _get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        create_res = await ac.post(
            "/api/languages/profile",
            json={
                "target_language": "Inglês",
                "learning_focus": "business",
            },
        )
        assert create_res.status_code == 201
        profile_id = create_res.json()["profile"]["id"]

        test_res = await ac.get(f"/api/languages/profiles/{profile_id}/placement-test")
        assert test_res.status_code == 200
        questions = test_res.json()["questions"]
        assert len(questions) == 10

        # Verifica posições da resposta correta nas opções
        positions = []
        for q in questions:
            assert q["correct_option"] in q["options"]
            pos = q["options"].index(q["correct_option"])
            positions.append(pos)

        # Não podem estar todas na posição 0
        assert not all(p == 0 for p in positions), "As respostas corretas ainda estão todas na primeira opção!"
        # Deve haver variedade de índices (ex: pelo menos 2 índices distintos entre 0, 1, 2, 3)
        assert len(set(positions)) >= 2, f"Distribuição das opções não está variada: {positions}"


@pytest.mark.asyncio
async def test_pronunciation_audio_analysis_endpoint():
    """Valida a rota de análise de áudio de dicção e pronúncia."""
    token = await _get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        create_res = await ac.post(
            "/api/languages/profile",
            json={
                "target_language": "Inglês",
                "learning_focus": "business",
            },
        )
        profile_id = create_res.json()["profile"]["id"]

        # Simula áudio em base64 (bytes válidos simulados)
        dummy_audio_b64 = "GkXfo59ChoEBQveBAULygQRC84EIQoKEd2VibUKHgQRChYECGFOAZwEAAAAAAAA=" * 3

        res = await ac.post(
            f"/api/languages/profiles/{profile_id}/pronunciation/analyze",
            json={
                "target_text": "We need to schedule an alignment meeting to mitigate the project bottleneck.",
                "audio_base64": dummy_audio_b64,
                "mime_type": "audio/webm",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "analysis" in data
        analysis = data["analysis"]
        assert "overall_score" in analysis
        assert "clarity_score" in analysis
        assert "coaching_instruction" in analysis
        assert analysis["overall_score"] >= 0


@pytest.mark.asyncio
async def test_open_conversation_practice_flow():
    """Valida o fluxo completo da área de conversação aberta no idioma ativo."""
    token = await _get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as ac:
        create_res = await ac.post(
            "/api/languages/profile",
            json={
                "target_language": "Inglês",
                "learning_focus": "business",
            },
        )
        profile_id = create_res.json()["profile"]["id"]

        # 1. Busca estado inicial da conversação
        conv_res = await ac.get(f"/api/languages/profiles/{profile_id}/conversation")
        assert conv_res.status_code == 200
        conv_data = conv_res.json()
        assert "topics" in conv_data
        assert len(conv_data["topics"]) >= 5
        assert len(conv_data["messages"]) == 0

        # 2. Envia mensagem do usuário
        send_res = await ac.post(
            f"/api/languages/profiles/{profile_id}/conversation/message",
            json={
                "message": "Hello Alex, I would like to review the delivery timeline for our next sprint.",
                "topic": "business_meeting",
            },
        )
        assert send_res.status_code == 200
        send_data = send_res.json()
        assert "user_message" in send_data
        assert "assistant_message" in send_data
        assert send_data["user_message"]["content"].startswith("Hello Alex")
        assert len(send_data["assistant_message"]["content"]) > 0
        assert "feedback" in send_data["assistant_message"]

        # 3. Consulta mensagens persistidas
        list_res = await ac.get(f"/api/languages/profiles/{profile_id}/conversation")
        assert list_res.status_code == 200
        assert len(list_res.json()["messages"]) == 2

        # 4. Limpa histórico de conversação
        del_res = await ac.delete(f"/api/languages/profiles/{profile_id}/conversation")
        assert del_res.status_code == 200

        # 5. Valida que histórico está vazio
        after_del = await ac.get(f"/api/languages/profiles/{profile_id}/conversation")
        assert len(after_del.json()["messages"]) == 0

