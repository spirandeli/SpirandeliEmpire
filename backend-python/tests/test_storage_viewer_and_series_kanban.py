import os
import shutil
import uuid
import pytest
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.future import select

from src.main import app
from src.database import AsyncSessionLocal
from src.models import Task, Business, User
from src.services.media.media_settings import (
    STORAGE_OUTPUT_DIR,
    get_task_output_dir,
)
from src.services.media.task_dispatcher import dispatch_series_video_tasks
from src.services.media.pipeline import _persist_video_progress


@pytest.mark.asyncio
async def test_storage_viewer_and_series_dispatch():
    rand = uuid.uuid4().hex[:6]
    email = f"operator_{rand}@spirandeli.io"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Registro de Operador
        reg_res = await ac.post("/api/auth/register", json={
            "name": f"Operador {rand}",
            "email": email,
            "password": "Password123!",
        })
        assert reg_res.status_code == 201
        token = reg_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Cria negócio Dark Channel
        biz_res = await ac.post("/api/businesses", json={
            "name": f"Império Dark {rand}",
            "archetype": "canal_dark",
            "niche": "Mistérios & Fatos Históricos",
            "description": "Produção autônoma de vídeos de alta retenção.",
        }, headers=headers)
        assert biz_res.status_code == 201
        biz_id = biz_res.json()["data"]["id"]

        # 3. ETAPA 1: Geração de Tarefas em Lote (Database Seeder / Task Dispatcher)
        # Dispara criação das 3 tarefas da Série 01 - A Queda de Lúcifer
        dispatch_res = await ac.post("/api/v1/storage/series/dispatch", json={
            "business_id": biz_id,
            "series_title": "Série 01 - A Queda de Lúcifer",
            "parts_count": 3,
            "auto_execute_part_1": False,
        }, headers=headers)
        assert dispatch_res.status_code == 200, dispatch_res.text
        dispatch_data = dispatch_res.json()
        assert dispatch_data["tasks_created"] == 3
        tasks = dispatch_data["tasks"]
        assert len(tasks) == 3

        part1 = tasks[0]
        part2 = tasks[1]
        part3 = tasks[2]

        assert part1["title"] == "[Vídeo] Série 01 - A Queda de Lúcifer - Parte 1 (Geração de Assets, TTS e FFmpeg)"
        assert part2["title"] == "[Vídeo] Série 01 - Parte 2 (Geração de Assets, TTS e FFmpeg)" or "Parte 2" in part2["title"]
        assert part3["title"] == "[Vídeo] Série 01 - Parte 3 (Geração de Assets, TTS e FFmpeg)" or "Parte 3" in part3["title"]

        # 4. ETAPA 1 (Status em Tempo Real): Worker -> Kanban
        # Testa a sequência de atualizações de 0% a 100%
        task_id = part1["id"]

        # 0%: Iniciando geração de prompts...
        await _persist_video_progress(
            task_id=task_id,
            business_id=biz_id,
            stage="prompts",
            percent=0.0,
        )

        async with AsyncSessionLocal() as session:
            t_res = await session.execute(select(Task).where(Task.id == task_id))
            t_db = t_res.scalar_one()
            assert "Iniciando geração de prompts... (0%)" in t_db.description
            assert t_db.payload["video_progress"]["percent"] == 0.0

        # 25%: Gerando imagens (Cena 5/20)...
        await _persist_video_progress(
            task_id=task_id,
            business_id=biz_id,
            current_scene=5,
            total_scenes=20,
            stage="images",
            percent=25.0,
        )

        async with AsyncSessionLocal() as session:
            t_res = await session.execute(select(Task).where(Task.id == task_id))
            t_db = t_res.scalar_one()
            assert "Gerando imagens (Cena 5/20)... (25%)" in t_db.description
            assert t_db.payload["video_progress"]["percent"] == 25.0

        # 50%: Gerando áudio TTS (ElevenLabs)...
        await _persist_video_progress(
            task_id=task_id,
            business_id=biz_id,
            stage="tts",
            percent=50.0,
        )

        async with AsyncSessionLocal() as session:
            t_res = await session.execute(select(Task).where(Task.id == task_id))
            t_db = t_res.scalar_one()
            assert "Gerando áudio TTS (ElevenLabs)... (50%)" in t_db.description
            assert t_db.payload["video_progress"]["percent"] == 50.0

        # 80%: Renderizando vídeo via FFmpeg...
        await _persist_video_progress(
            task_id=task_id,
            business_id=biz_id,
            stage="ffmpeg",
            percent=80.0,
        )

        async with AsyncSessionLocal() as session:
            t_res = await session.execute(select(Task).where(Task.id == task_id))
            t_db = t_res.scalar_one()
            assert "Renderizando vídeo via FFmpeg... (80%)" in t_db.description
            assert t_db.payload["video_progress"]["percent"] == 80.0

        # 100%: Concluído. Arquivo salvo em /app/storage/output/
        await _persist_video_progress(
            task_id=task_id,
            business_id=biz_id,
            stage="done",
            percent=100.0,
            is_completed=True,
            output_path="/app/storage/output/",
        )

        async with AsyncSessionLocal() as session:
            t_res = await session.execute(select(Task).where(Task.id == task_id))
            t_db = t_res.scalar_one()
            assert "Concluído. Arquivo salvo em /app/storage/output/ (100%)" in t_db.description
            assert t_db.payload["video_progress"]["percent"] == 100.0
            assert t_db.status == "done"
            assert t_db.completed_at is not None

        # 5. ETAPA 2: Cria arquivos simulados em /app/storage/output/ para verificar Storage Viewer
        task_out = get_task_output_dir(biz_id, task_id)
        video_sample = task_out / f"video_dark_task_{task_id}.mp4"
        audio_sample = task_out / "narration.mp3"
        scenes_dir = task_out / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        img_sample = scenes_dir / "scene_01.png"

        video_sample.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mock video data")
        audio_sample.write_bytes(b"\xff\xfb\x90\x00mock mp3 audio data")
        img_sample.write_bytes(b"\x89PNG\r\n\x1a\n\x00mock png data")

        # 6. ETAPA 2: Endpoint de Listagem GET /api/v1/storage/outputs
        out_res = await ac.get("/api/v1/storage/outputs", headers=headers)
        assert out_res.status_code == 200, out_res.text
        out_data = out_res.json()
        assert out_data["status"] == "success"
        assert out_data["total_files"] >= 3
        assert len(out_data["groups"]) >= 1

        # Verifica agrupamento por business_id e task_id
        target_group = next((g for g in out_data["groups"] if g["business_id"] == biz_id), None)
        assert target_group is not None
        assert target_group["business_name"] == f"Império Dark {rand}"

        target_task = next((t for t in target_group["tasks"] if t["task_id"] == task_id), None)
        assert target_task is not None
        assert target_task["task_title"] == part1["title"]
        assert target_task["video_count"] >= 1
        assert target_task["audio_count"] >= 1
        assert target_task["image_count"] >= 1

        # Verifica URLs estáticas seguras
        assert target_task["primary_video"]["static_url"] == f"/outputs/biz_{biz_id}/task_{task_id}/video_dark_task_{task_id}.mp4"
        assert target_task["primary_video"]["extension"] == ".mp4"
        assert target_task["primary_video"]["type"] == "video"
        assert "modified_at" in target_task["primary_video"]
        assert "size_mb" in target_task["primary_video"]

        # 7. Testa se o endpoint estático /outputs serve o arquivo
        static_req = await ac.get(target_task["primary_video"]["static_url"])
        assert static_req.status_code == 200
        assert b"ftypmp42" in static_req.content

