import os
import uuid
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select

from src.main import app
from src.database import AsyncSessionLocal
from src.models import Task
from src.services.media.agents import (
    AgentContext,
    AgentStage,
    AssemblerAgent,
    NarrationAgent,
    ScriptAgent,
    SubtitleAgent,
    VideoOrchestrator,
    VideoSceneAgent,
    load_manifest,
)
from src.services.media.agents.script_agent import validate_and_polish_script
from src.services.media.tts_service import normalize_ptbr_for_speech
from src.services.media.subtitle_service import _build_chunks_from_word_timings, generate_subtitles


def test_ptbr_speech_normalization():
    raw = "[pausa] Cena 1: Em 1977, 90% dos dados custaram R$ 50."
    norm = normalize_ptbr_for_speech(raw)
    assert "[pausa]" not in norm
    assert "Cena 1" not in norm
    assert "mil novecentos e setenta e sete" in norm
    assert "noventa por cento" in norm
    assert "cinquenta reais" in norm


def test_subtitle_prosodic_chunking_and_karaoke_ass(tmp_path):
    words = [
        {"text": "O", "punctuated_text": "O", "start": 0.05, "end": 0.15, "sentence_end": False},
        {"text": "segredo", "punctuated_text": "segredo", "start": 0.16, "end": 0.50, "sentence_end": False},
        {"text": "do", "punctuated_text": "do", "start": 0.51, "end": 0.62, "sentence_end": False},
        {"text": "universo", "punctuated_text": "universo.", "start": 0.63, "end": 1.10, "sentence_end": True},
        {"text": "Ninguém", "punctuated_text": "Ninguém", "start": 1.35, "end": 1.75, "sentence_end": False},
        {"text": "esperava", "punctuated_text": "esperava", "start": 1.76, "end": 2.15, "sentence_end": False},
        {"text": "essa", "punctuated_text": "essa", "start": 2.16, "end": 2.38, "sentence_end": False},
        {"text": "revelação", "punctuated_text": "revelação.", "start": 2.39, "end": 2.95, "sentence_end": True},
    ]
    chunks = _build_chunks_from_word_timings(words, max_words=4)
    assert len(chunks) == 3
    assert chunks[0]["text"] == "O SEGREDO DO UNIVERSO"
    assert chunks[1]["text"] == "NINGUÉM ESPERAVA"
    assert chunks[2]["text"] == "ESSA REVELAÇÃO"
    assert len(chunks[0]["words"]) == 4

    srt_p = str(tmp_path / "out.srt")
    ass_p = str(tmp_path / "out.ass")
    res = generate_subtitles(
        scenes_timing=[{"scene_number": 1, "text": "O segredo do universo.", "start": 0.0, "end": 3.0}],
        output_srt_path=srt_p,
        output_ass_path=ass_p,
        word_timings=words,
        style_preset="hormozi_karaoke",
    )
    ass_content = Path(ass_p).read_text(encoding="utf-8")
    assert "\\fscx108\\fscy108" in ass_content
    assert res["chunks_count"] == 3
    assert res["events_count"] == 8


@pytest.mark.asyncio
async def test_script_agent_adaptive_visual_bible_no_forced_anime(tmp_path):
    os.environ["ABVOS_DISABLE_EXTERNAL_IMAGE_API"] = "1"
    ctx = AgentContext(
        task_id=77001,
        business_id=88001,
        user_id=1,
        title="Como as Startups de IA Economizam Energia",
        topic="Infraestrutura de data centers modernos e eficiência energética",
        business_niche="Tecnologia & Negócios",
        visual_style="",
        pause_after_script=True,
    )
    agent = ScriptAgent()
    manifest = load_manifest(ctx)
    manifest = await agent.run(ctx, manifest, force_regenerate=True)

    assert manifest.script is not None
    assert len(manifest.script.scenes) >= 12
    # Não deve forçar Castlevania / Lúcifer em tema de tecnologia
    assert "castlevania" not in manifest.script.visual_bible.art_style.lower()
    assert "lucifer" not in manifest.script.visual_bible.protagonist_description.lower()
    assert manifest.script.word_count > 40
    for sc in manifest.script.scenes:
        assert "[" not in sc.narration
        assert sc.camera_motion in ("zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up")


@pytest.mark.asyncio
async def test_five_agents_full_pipeline_pause_and_continue_api(monkeypatch):
    os.environ["ABVOS_DISABLE_EXTERNAL_IMAGE_API"] = "1"
    rand = uuid.uuid4().hex[:6]
    email = f"agents_{rand}@spirandeli.io"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        reg = await ac.post("/api/auth/register", json={
            "name": f"Agent Tester {rand}",
            "email": email,
            "password": "Password123!",
        })
        assert reg.status_code == 201
        token = reg.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        biz = await ac.post("/api/businesses", json={
            "name": f"Canal Fatos {rand}",
            "archetype": "canal_dark",
            "niche": "Mistérios Históricos",
        }, headers=headers)
        assert biz.status_code == 201
        biz_id = biz.json()["data"]["id"]

        # 1. Cria pauta no Dark Studio -> deve executar Agente 1 e pausar em supervisão com 5 subtarefas
        script_res = await ac.post(f"/api/businesses/{biz_id}/dark-studio/generate-script", json={
            "title": "O Enigma do Farol Desaparecido",
            "topic": "Três faroleiros desapareceram sem deixar vestígios em 1900.",
            "format_type": "short",
            "target_platform": "youtube_shorts",
        }, headers=headers)
        assert script_res.status_code == 201, script_res.text
        parent_task_id = script_res.json()["data"]["task_id"]

        # Verifica manifesto e as 5 subtarefas via GET /pipeline
        pipe_res = await ac.get(f"/api/tasks/{parent_task_id}/pipeline", headers=headers)
        assert pipe_res.status_code == 200, pipe_res.text
        pipe_data = pipe_res.json()["data"]
        assert pipe_data["script_approved"] is False
        assert len(pipe_data["stages"]) == 5
        assert [s["stage"] for s in pipe_data["stages"]] == [
            "script", "video_scenes", "narration", "subtitles", "assemble"
        ]
        assert pipe_data["stages"][0]["manifest_status"] == "completed"
        assert pipe_data["stages"][1]["manifest_status"] == "pending"

        # Verifica que as 5 subtarefas foram criadas no banco com parent_id = parent_task_id
        async with AsyncSessionLocal() as session:
            sub_res = await session.execute(
                select(Task).where(Task.parent_id == parent_task_id, Task.deleted_at.is_(None))
            )
            subs = sub_res.scalars().all()
            assert len(subs) == 5

        # 2. Aprova e continua para Agentes 2 a 5 em modo sync para validar resultado completo
        # Encurta para 3 cenas no manifest em disco para teste rápido de FFmpeg + TTS
        async with AsyncSessionLocal() as session:
            t_res = await session.execute(select(Task).where(Task.id == parent_task_id))
            parent_obj = t_res.scalar_one()
            ctx = await VideoOrchestrator().build_context(session, parent_obj, parent_obj.user if hasattr(parent_obj, "user") and parent_obj.user else None) if False else None

        # Simula aprovação via endpoint /agents/continue?sync=true usando um roteiro compacto de 3 cenas para execução rápida
        # Ajustando o manifest para 3 cenas antes do continue
        from src.services.media.media_settings import get_task_media_dir
        import json
        manifest_file = get_task_media_dir(biz_id, parent_task_id) / "pipeline_manifest.json"
        m_raw = json.loads(manifest_file.read_text(encoding="utf-8"))
        m_raw["script"]["scenes"] = m_raw["script"]["scenes"][:3]
        manifest_file.write_text(json.dumps(m_raw), encoding="utf-8")

        cont_res = await ac.post(f"/api/tasks/{parent_task_id}/agents/continue?sync=true", headers=headers)
        assert cont_res.status_code == 200, cont_res.text
        cont_data = cont_res.json()["data"]
        assert cont_data["status"] == "done"
        assert cont_data["result"]["video_url"].endswith(".mp4")
        assert cont_data["result"]["audio_url"].endswith(".mp3")
        assert cont_data["result"]["srt_url"].endswith(".srt")

        final_mp4 = cont_data["result"]["media"]["video"]["path"]
        assert Path(final_mp4).exists() and Path(final_mp4).stat().st_size > 0
        assert cont_data["result"]["media"]["video"]["ffprobe_verified"] is True

        # 3. Testa regeneração unitária da Cena #2 via endpoint
        regen_res = await ac.post(
            f"/api/tasks/{parent_task_id}/scenes/2/regenerate",
            json={"custom_prompt": "Wide lighthouse storm shot 9:16", "reassemble": False, "sync": True},
            headers=headers,
        )
        assert regen_res.status_code == 200, regen_res.text
        assert regen_res.json()["data"]["scene_number"] == 2
