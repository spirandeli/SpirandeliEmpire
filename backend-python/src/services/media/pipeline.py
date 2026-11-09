import asyncio
import functools
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.services.media.media_settings import (
    get_task_media_dir,
    get_task_output_dir,
    STORAGE_OUTPUT_DIR,
)
from src.services.media.image_service import (
    generate_all_scene_images,
    create_cinematic_dark_backdrop,
)
from src.services.media.tts_service import synthesize_narration
from src.services.media.subtitle_service import generate_subtitles
from src.services.media.video_renderer import render_video_with_audio_and_subtitles
import shutil

logger = logging.getLogger("abvos.media.pipeline")


class TaskRouter:
    """
    Router de tarefas assíncronas do motor ABVOS (compatível com ARQ, Celery e FastAPI Background).
    Permite registrar tasks com decorators contendo job_timeout e metadados de execução.
    """
    def __init__(self):
        self._tasks: Dict[str, Any] = {}

    def task(self, job_timeout: Optional[int] = None, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kw):
                # Se for chamado pelo ARQ Worker, o primeiro argumento pode ser o 'ctx' do worker
                if args and (isinstance(args[0], dict) or hasattr(args[0], "redis")):
                    return await func(*args[1:], **kw)
                return await func(*args, **kw)

            wrapper.job_timeout = job_timeout
            wrapper.task_kwargs = kwargs
            wrapper._raw_func = func
            self._tasks[func.__name__] = wrapper
            return wrapper
        return decorator

    def get_task(self, name: str):
        return self._tasks.get(name)

    @property
    def registered_tasks(self) -> Dict[str, Any]:
        return self._tasks


router = TaskRouter()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _persist_video_progress(
    task_id: int,
    business_id: int,
    current_scene: int = 0,
    total_scenes: int = 20,
    status_text: Optional[str] = None,
    percent: Optional[float] = None,
    stage: Optional[str] = None,
    is_completed: bool = False,
    output_path: Optional[str] = None,
):
    """
    Atualiza o progresso no banco de dados (tabela tasks, campos status_log, description, status e payload)
    em tempo real para refletir a pipeline no Kanban:
    - Iniciando geração de prompts... (0%)
    - Gerando imagens (Cena 5/20)... (25%)
    - Gerando áudio TTS (ElevenLabs)... (50%)
    - Renderizando vídeo via FFmpeg... (80%)
    - Concluído. Arquivo salvo em /app/storage/output/ (100%)
    """
    if percent is None:
        if is_completed or stage == "done":
            percent = 100.0
        elif stage == "prompts":
            percent = 0.0
        elif stage == "tts":
            percent = 50.0
        elif stage == "ffmpeg":
            percent = 80.0
        elif stage == "images" or current_scene > 0:
            percent = round((current_scene / total_scenes) * 100, 1) if total_scenes else 0.0
        else:
            percent = 0.0

    if not status_text:
        if percent == 0 or stage == "prompts":
            status_text = "Iniciando geração de prompts..."
        elif stage == "images":
            status_text = f"Gerando imagens (Cena {current_scene}/{total_scenes})..."
        elif stage == "tts" or percent == 50:
            status_text = "Gerando áudio TTS (ElevenLabs)..."
        elif stage == "ffmpeg" or percent == 80:
            status_text = "Renderizando vídeo via FFmpeg..."
        elif is_completed or percent == 100 or stage == "done":
            status_text = f"Concluído. Arquivo salvo em {output_path or '/app/storage/output/'}"
        else:
            status_text = f"Processando vídeo ({current_scene}/{total_scenes})..."

    formatted_msg = f"{status_text} ({int(percent)}%)" if not status_text.endswith("%)") else status_text

    try:
        from src.database import AsyncSessionLocal
        from src.models import Task, AgentLog
        from sqlalchemy.future import select

        now = _utc_now()

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Task).where(Task.id == task_id))
            task = res.scalar_one_or_none()
            if task:
                task.status_log = formatted_msg

                # Atualiza description mantendo o histórico/instrução original
                orig_desc = task.description or ""
                clean_lines = [
                    l for l in orig_desc.splitlines()
                    if not re.match(r"^(?:\[Progresso|\b(?:Iniciando|Gerando|Renderizando|Concluído).*?\(\d+%\))", l.strip(), re.IGNORECASE)
                ]
                clean_orig = "\n".join(clean_lines).strip()
                task.description = f"{formatted_msg}\n\n{clean_orig}".strip() if clean_orig else formatted_msg

                payload_data = dict(task.payload or {})
                payload_data["video_progress"] = {
                    "stage": stage or ("done" if is_completed else "running"),
                    "current_scene": current_scene,
                    "total_scenes": total_scenes,
                    "percent": percent,
                    "status_log": formatted_msg,
                    "output_path": output_path or "/app/storage/output/",
                    "updated_at": now.isoformat(),
                }
                task.payload = payload_data
                task.updated_at = now

                if is_completed or percent >= 100:
                    task.status = "done"
                    task.completed_at = now

                # Registra evento na tabela agent_logs para streaming em tempo real no frontend
                agent_log = AgentLog(
                    user_id=task.user_id,
                    business_id=task.business_id or business_id,
                    task_id=task.id,
                    level="info",
                    event="video_scene_progress",
                    message=f"IA Worker ABVOS: {formatted_msg}",
                    context={
                        "task_id": task.id,
                        "current_scene": current_scene,
                        "total_scenes": total_scenes,
                        "percent": percent,
                        "stage": stage,
                    },
                    created_at=now,
                )
                session.add(agent_log)
                await session.commit()
                logger.info(f"[Task #{task_id}] Progresso persistido no banco: {formatted_msg}")
    except Exception as db_err:
        logger.warning(f"[Task #{task_id}] Falha não-bloqueante ao persistir progresso no banco: {db_err}")


def ensure_twenty_scenes(
    scenes: Optional[List[Dict[str, Any]]],
    full_narration: str,
    title: str = "Vídeo Dark",
) -> List[Dict[str, Any]]:
    """
    Garante obrigatoriamente 20 cenas de 3 segundos (totalizando exatamente 60 segundos por vídeo),
    distribuídas estrategicamente em:
    - Part 1: Cenas 01 a 06 (0s a 18s) - Hook Hipnótico e Quebra de Padrão
    - Part 2: Cenas 07 a 15 (18s a 45s) - Desenvolvimento e Tensão Narrativa
    - Part 3: Cenas 16 a 20 (45s a 60s) - Clímax, CTA e Looping Contínuo
    """
    camera_styles = [
        "Dynamic macro push-in, anamorphic lens, volumetric dark fog",
        "Wide cinematic angle, ominous shadows, Unreal Engine 5 render",
        "Extreme close up on critical detail, dramatic side lighting",
        "Slow atmospheric dolly in, cold blue rim light, 8k resolution",
        "Dutch angle view, dark neo-noir mystery, hyper-realistic particles",
        "Low-angle heroic shot in total darkness, neon crimson accent",
    ]

    base_narration_chunks = []
    if full_narration:
        # Divide narração em frases ou orações
        clean = re.sub(r"\s+", " ", full_narration).strip()
        parts = [p.strip() for p in re.split(r"[.!?]+", clean) if len(p.strip()) > 3]
        base_narration_chunks = parts

    normalized_scenes: List[Dict[str, Any]] = []

    # Caso já tenhamos cenas estruturadas fornecidas
    input_scenes = list(scenes or [])

    if len(input_scenes) >= 20:
        # Se vieram 20 ou mais, seleciona as 20 primeiras e padroniza para 3 segundos cada
        for i in range(20):
            sc = input_scenes[i]
            normalized_scenes.append({
                "scene_number": i + 1,
                "duration": 3.0,
                "narration": sc.get("narration") or sc.get("script") or f"Parte {i + 1} de {title}",
                "visual_prompt": sc.get("visual_prompt") or f"Cinematic scene #{i + 1} for {title}, {camera_styles[i % len(camera_styles)]}, 9:16",
                "on_screen_text": sc.get("on_screen_text") or sc.get("title") or f"PARTE {i + 1}",
            })
        return normalized_scenes

    # Se vieram menos de 20 cenas, expande uniformemente para preencher as 20 cenas de 3s
    if input_scenes:
        ratio = 20 / len(input_scenes)
        for i in range(20):
            src_idx = min(int(i / ratio), len(input_scenes) - 1)
            src_scene = input_scenes[src_idx]
            sub_part = (i % int(max(1, ratio))) + 1
            cam = camera_styles[i % len(camera_styles)]

            narr = src_scene.get("narration") or src_scene.get("script") or title
            v_prompt = src_scene.get("visual_prompt") or f"Dramatic cinematic shot for {title}"

            normalized_scenes.append({
                "scene_number": i + 1,
                "duration": 3.0,
                "narration": narr if sub_part == 1 else f"{narr} (fase {sub_part})",
                "visual_prompt": f"{v_prompt}, angle #{sub_part}, {cam}, aspect ratio 9:16",
                "on_screen_text": src_scene.get("on_screen_text") or f"CENA {i + 1}",
            })
        return normalized_scenes

    # Fallback estruturado criando 20 cenas a partir do texto de narração ou título
    for i in range(20):
        cam = camera_styles[i % len(camera_styles)]
        part_name = "Part 1 (Hook)" if i < 6 else ("Part 2 (Escalation)" if i < 15 else "Part 3 (Climax)")

        narr_text = ""
        if base_narration_chunks:
            narr_text = base_narration_chunks[i % len(base_narration_chunks)]
        else:
            narr_text = f"O mistério sombrio e os segredos proibidos de {title} no fragmento #{i + 1}."

        normalized_scenes.append({
            "scene_number": i + 1,
            "duration": 3.0,
            "narration": narr_text,
            "visual_prompt": f"Dark epic cinematic illustration depicting: {narr_text} — Context: {title}, scene #{i + 1}, {cam}, 8k resolution, volumetric lighting, vertical 9:16",
            "on_screen_text": f"CENA {i + 1:02d}: {part_name.upper()}",
        })

    return normalized_scenes


@router.task(job_timeout=None)
async def execute_full_video_pipeline(
    task_id: int,
    business_id: int,
    scenes: Optional[List[Dict[str, Any]]] = None,
    full_narration: Optional[str] = None,
    voice_persona: Optional[str] = None,
    gemini_key: Optional[str] = None,
    elevenlabs_key: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Motor Principal de Renderização Multimídia Autônoma ABVOS (Vídeo 9:16, 1080x1920):
    1. job_timeout=None (Timeout Infinite): Sem limite de tempo no ARQ/Redis/FastAPI.
    2. Execução Sequencial Garantida (20 Cenas de 3s cada = exatamente 60s / 1 minuto).
    3. Retry automático (3 tentativas por cena) com fallback para imagem de segurança se a IA demorar.
    4. Log e persistência de progresso a cada 5 cenas no banco de dados (tasks.status_log e description).
    5. Confirmação rigorosa dos assets das 20 cenas antes de disparar FFmpeg.
    6. Compilação final via FFmpeg de exatamente 1 minuto de duração (sem cortes).
    """
    task_media_dir = get_task_media_dir(business_id, task_id)
    task_output_dir = get_task_output_dir(business_id, task_id)
    scenes_dir = task_media_dir / "scenes"
    audio_path = str(task_media_dir / "narration.mp3")
    srt_path = str(task_media_dir / "subtitles.srt")
    ass_path = str(task_media_dir / "subtitles.ass")
    final_video_path = str(task_media_dir / f"video_dark_task_{task_id}.mp4")

    logger.info(f"== [ABVOS VIDEO WORKER] INICIANDO PIPELINE (TASK #{task_id}, BIZ #{business_id}) ==")
    # ETAPA 1: Iniciando geração de prompts... (0%)
    await _persist_video_progress(
        task_id=task_id,
        business_id=business_id,
        current_scene=0,
        total_scenes=20,
        stage="prompts",
        percent=0.0,
    )

    # Se faltar chave ou narração, tenta resolver via banco
    task_title = f"Task #{task_id}"
    if not full_narration or not scenes or not gemini_key:
        try:
            from src.database import AsyncSessionLocal
            from src.models import Task, User
            from sqlalchemy.future import select
            from sqlalchemy.orm import selectinload

            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    select(Task).options(selectinload(Task.business)).where(Task.id == task_id)
                )
                db_task = res.scalar_one_or_none()
                if db_task:
                    task_title = db_task.title
                    if not full_narration:
                        full_narration = db_task.description or db_task.title
                    if not gemini_key:
                        try:
                            from src.services.jeffrey_orchestrator import get_effective_gemini_key
                            u_res = await session.execute(select(User).where(User.id == db_task.user_id))
                            db_user = u_res.scalar_one_or_none()
                            if db_user:
                                gemini_key = await get_effective_gemini_key(db_user, session)
                        except Exception:
                            pass
        except Exception as load_err:
            logger.warning(f"Não foi possível carregar dados complementares do banco: {load_err}")

    # PASSO 1: Normalização Garantida de 20 Cenas (3 segundos cada, total 60 segundos)
    twenty_scenes = ensure_twenty_scenes(scenes, full_narration or task_title, title=task_title)
    total_scenes_count = len(twenty_scenes)
    assert total_scenes_count == 20, f"O pipeline exige exatamente 20 cenas, obtido {total_scenes_count}"

    # PASSO 2: Execução Sequencial das 20 Cenas com Retry (3x) e Persistência de Progresso a cada 5 cenas
    logger.info(f"[Passo 1/4] Iterando sequencialmente pelas 20 cenas (Part 1, Part 2 e Part 3)...")

    async def _on_scene_progress(current_sc: int, total_sc: int):
        # A cada 5 cenas processadas ou na última cena, atualiza o banco de dados
        # Ex: Cena 5/20 -> 25%, Cena 10/20 -> 50%, etc.
        if current_sc % 5 == 0 or current_sc == 1 or current_sc == total_sc:
            sc_pct = round((current_sc / total_sc) * 100, 1)
            # No requisito exato: Cena 5/20 -> 25%
            if current_sc == 5:
                sc_pct = 25.0
            await _persist_video_progress(
                task_id=task_id,
                business_id=business_id,
                current_scene=current_sc,
                total_scenes=total_sc,
                stage="images",
                percent=sc_pct,
            )

    image_paths = await generate_all_scene_images(
        scenes=twenty_scenes,
        output_dir=scenes_dir,
        gemini_key=gemini_key,
        progress_callback=_on_scene_progress,
        sequential=True,
    )

    # PASSO 3: Síntese de Narração de Áudio (TTS)
    logger.info("[Passo 2/4] Sintetizando narração em áudio para o vídeo...")
    # ETAPA 3: Gerando áudio TTS (ElevenLabs)... (50%)
    await _persist_video_progress(
        task_id=task_id,
        business_id=business_id,
        current_scene=10,
        total_scenes=20,
        stage="tts",
        percent=50.0,
    )
    audio_text = full_narration or " ".join([sc.get("narration", "") for sc in twenty_scenes])
    tts_result = await synthesize_narration(
        text=audio_text,
        output_path=audio_path,
        elevenlabs_key=elevenlabs_key,
        preferred_voice=voice_persona,
    )
    total_audio_duration = tts_result["duration_seconds"]

    # PASSO 4: Geração de Legendas Dinâmicas Sincronizadas (20 Cenas x 3.0s = 60.0s)
    logger.info("[Passo 3/4] Gerando legendas dinâmicas de alta retenção (20 cenas x 3.0s = 60.0s)...")
    duration_per_scene = 3.0  # Cada cena tem rigorosamente 3 segundos
    scenes_timing = []
    for i, sc in enumerate(twenty_scenes):
        scenes_timing.append({
            "text": sc.get("narration") or sc.get("on_screen_text") or "",
            "start": round(i * duration_per_scene, 2),
            "end": round((i + 1) * duration_per_scene, 2),
        })

    subtitles_result = generate_subtitles(
        scenes_timing=scenes_timing,
        output_srt_path=srt_path,
        output_ass_path=ass_path,
    )

    # PASSO 5: Confirmação Estrita dos Assets Antes de Disparar FFmpeg
    logger.info("[Passo 4/4] Validando integridade física dos assets antes da compilação FFmpeg...")
    verified_images: List[str] = []
    for i in range(1, 21):
        sc_file = scenes_dir / f"scene_{i:02d}.jpg"
        if not sc_file.exists() or sc_file.stat().st_size == 0:
            logger.warning(f"Asset da cena #{i} ausente no disco. Gerando imagem de segurança para garantir integridade física.")
            sc_meta = twenty_scenes[i - 1] if i - 1 < len(twenty_scenes) else {}
            fallback = create_cinematic_dark_backdrop(
                width=1080,
                height=1920,
                scene_number=i,
                title=sc_meta.get("on_screen_text") or f"Cena {i}",
                prompt=sc_meta.get("narration") or sc_meta.get("visual_prompt") or "",
            )
            fallback.save(str(sc_file), "JPEG", quality=92)
        verified_images.append(str(sc_file))

    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise FileNotFoundError(f"Asset de áudio {audio_path} não foi confirmado no disco antes do FFmpeg.")

    assert len(verified_images) == 20, f"Confirmação falhou: esperado 20 assets de imagem, encontrado {len(verified_images)}"

    # ETAPA 4: Renderizando vídeo via FFmpeg... (80%)
    await _persist_video_progress(
        task_id=task_id,
        business_id=business_id,
        current_scene=20,
        total_scenes=20,
        stage="ffmpeg",
        percent=80.0,
    )

    # PASSO 6: Compilação Final via FFmpeg (Exatamente 1 minuto / 60 segundos de duração)
    render_result = await render_video_with_audio_and_subtitles(
        image_paths=verified_images,
        audio_path=audio_path,
        output_video_path=final_video_path,
        subtitle_ass_path=ass_path,
        fps=30,
        width=1080,
        height=1920,
        scene_duration=3.0,
    )

    # Sincroniza e garante os artefatos finais no diretório de saída oficial /app/storage/output
    output_video_file = task_output_dir / f"video_dark_task_{task_id}.mp4"
    output_audio_file = task_output_dir / "narration.mp3"
    output_srt_file = task_output_dir / "subtitles.srt"
    output_scenes_dir = task_output_dir / "scenes"
    output_scenes_dir.mkdir(parents=True, exist_ok=True)

    try:
        if os.path.exists(final_video_path):
            shutil.copy2(final_video_path, str(output_video_file))
        if os.path.exists(audio_path):
            shutil.copy2(audio_path, str(output_audio_file))
        if os.path.exists(srt_path):
            shutil.copy2(srt_path, str(output_srt_file))
        for v_img in verified_images:
            if os.path.exists(v_img):
                shutil.copy2(v_img, str(output_scenes_dir / Path(v_img).name))
    except Exception as copy_err:
        logger.warning(f"Aviso ao copiar arquivos para /app/storage/output: {copy_err}")

    # ETAPA 5: Concluído. Arquivo salvo em /app/storage/output/ (100%)
    await _persist_video_progress(
        task_id=task_id,
        business_id=business_id,
        current_scene=20,
        total_scenes=20,
        stage="done",
        percent=100.0,
        is_completed=True,
        output_path="/app/storage/output/",
    )

    video_relative_url = f"/outputs/biz_{business_id}/task_{task_id}/video_dark_task_{task_id}.mp4"
    audio_relative_url = f"/outputs/biz_{business_id}/task_{task_id}/narration.mp3"
    srt_relative_url = f"/outputs/biz_{business_id}/task_{task_id}/subtitles.srt"

    result_manifest = {
        "success": True,
        "business_id": business_id,
        "task_id": task_id,
        "scenes_count": 20,
        "video": {
            "path": final_video_path,
            "url": video_relative_url,
            "resolution": render_result.get("resolution", "1080x1920"),
            "aspect_ratio": "9:16",
            "duration_seconds": 60.0,
            "size_mb": render_result.get("size_mb", 0.0),
        },
        "audio": {
            "path": audio_path,
            "url": audio_relative_url,
            "duration_seconds": total_audio_duration,
            "provider": tts_result.get("provider", "edge_tts"),
        },
        "subtitles": {
            "srt_path": srt_path,
            "srt_url": srt_relative_url,
            "ass_path": ass_path,
        },
        "images_generated": [
            f"/api/media/file/biz_{business_id}/task_{task_id}/scenes/{Path(p).name}"
            for p in verified_images
        ],
    }

    logger.info(f"== PIPELINE MULTIMÍDIA CONCLUÍDO COM SUCESSO! Vídeo 60s: {final_video_path} ==")
    return result_manifest


# Alias para retrocompatibilidade
execute_full_media_pipeline = execute_full_video_pipeline
