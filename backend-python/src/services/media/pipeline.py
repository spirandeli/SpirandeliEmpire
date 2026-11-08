import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.services.media.media_settings import get_task_media_dir
from src.services.media.image_service import generate_all_scene_images
from src.services.media.tts_service import synthesize_narration
from src.services.media.subtitle_service import generate_subtitles
from src.services.media.video_renderer import render_video_with_audio_and_subtitles

logger = logging.getLogger("abvos.media.pipeline")


async def execute_full_media_pipeline(
    business_id: int,
    task_id: int,
    scenes: List[Dict[str, Any]],
    full_narration: str,
    voice_persona: Optional[str] = None,
    gemini_key: Optional[str] = None,
    elevenlabs_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executa o Pipeline Multimídia Autônomo completo do ABVOS:
    Texto/Prompts -> Geração Visual -> Síntese TTS -> Legendas Dinâmicas -> Renderização FFmpeg (MP4 9:16).
    """
    task_media_dir = get_task_media_dir(business_id, task_id)
    scenes_dir = task_media_dir / "scenes"
    audio_path = str(task_media_dir / "narration.mp3")
    srt_path = str(task_media_dir / "subtitles.srt")
    ass_path = str(task_media_dir / "subtitles.ass")
    final_video_path = str(task_media_dir / f"video_dark_task_{task_id}.mp4")

    logger.info(f"== INICIANDO PIPELINE MULTIMÍDIA PARA TASK #{task_id} (BIZ #{business_id}) ==")

    # Se não houver cenas fornecidas, cria blocos baseados no texto
    if not scenes and full_narration:
        sentences = [s.strip() for s in full_narration.split(".") if len(s.strip()) > 5]
        scenes = [
            {
                "scene_number": i + 1,
                "narration": s,
                "visual_prompt": f"Dramatic cinematic shot representing: {s[:60]}, 8k dark anime style, 9:16",
            }
            for i, s in enumerate(sentences[:20])
        ]

    # PASSO 1: Geração Visual das Imagens
    logger.info(f"[Passo 1/4] Gerando {len(scenes)} imagens de cenas em 9:16...")
    image_paths = await generate_all_scene_images(
        scenes=scenes,
        output_dir=scenes_dir,
        gemini_key=gemini_key,
    )

    # PASSO 2: Síntese de Voz (TTS)
    logger.info("[Passo 2/4] Sintetizando narração de alta fidelidade...")
    tts_result = await synthesize_narration(
        text=full_narration or " ".join([sc.get("narration", "") for sc in scenes]),
        output_path=audio_path,
        elevenlabs_key=elevenlabs_key,
    )
    total_audio_duration = tts_result["duration_seconds"]

    # PASSO 3: Geração de Legendas Dinâmicas Sincronizadas
    logger.info("[Passo 3/4] Alinhando legendas no estilo Alex Hormozi...")
    num_scenes = max(1, len(scenes))
    duration_per_scene = total_audio_duration / num_scenes

    scenes_timing = []
    for i, sc in enumerate(scenes):
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

    # PASSO 4: Renderização do Vídeo Final com FFmpeg
    logger.info("[Passo 4/4] Renderizando vídeo 1080x1920 (9:16) no motor FFmpeg...")
    render_result = await render_video_with_audio_and_subtitles(
        image_paths=image_paths,
        audio_path=audio_path,
        output_video_path=final_video_path,
        subtitle_ass_path=ass_path,
        fps=30,
        width=1080,
        height=1920,
        scene_duration=duration_per_scene,
    )

    # URLs relativas para a API do ABVOS
    video_relative_url = f"/api/media/file/biz_{business_id}/task_{task_id}/video_dark_task_{task_id}.mp4"
    audio_relative_url = f"/api/media/file/biz_{business_id}/task_{task_id}/narration.mp3"
    srt_relative_url = f"/api/media/file/biz_{business_id}/task_{task_id}/subtitles.srt"

    result_manifest = {
        "success": True,
        "business_id": business_id,
        "task_id": task_id,
        "scenes_count": len(image_paths),
        "video": {
            "path": final_video_path,
            "url": video_relative_url,
            "resolution": render_result.get("resolution", "1080x1920"),
            "aspect_ratio": "9:16",
            "duration_seconds": render_result.get("duration_seconds", total_audio_duration),
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
            for p in image_paths
        ],
    }

    logger.info(f"== PIPELINE MULTIMÍDIA CONCLUÍDO COM SUCESSO! Vídeo: {final_video_path} ==")
    return result_manifest

