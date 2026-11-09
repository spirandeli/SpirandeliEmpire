import os
import shutil
import pytest
from pathlib import Path
from src.services.media.pipeline import (
    execute_full_media_pipeline,
    execute_full_video_pipeline,
    ensure_twenty_scenes,
    router,
)
from src.services.media.media_settings import (
    get_ffmpeg_path,
    get_ffprobe_path,
    STORAGE_MEDIA_DIR,
    STORAGE_OUTPUT_DIR,
)
from src.worker import WorkerSettings


def test_ffmpeg_and_ffprobe_available():
    ffmpeg = get_ffmpeg_path()
    ffprobe = get_ffprobe_path()
    assert Path(ffmpeg).exists(), f"FFmpeg não encontrado em {ffmpeg}"
    assert Path(ffprobe).exists(), f"FFprobe não encontrado em {ffprobe}"


def test_video_worker_infinite_timeout_configuration():
    """Valida a Instrução 1: Remoção de timeout e configuração job_timeout=None no ARQ/Router."""
    # 1. Verifica no router ABVOS
    task_func = router.get_task("execute_full_video_pipeline")
    assert task_func is not None, "execute_full_video_pipeline não está registrada no router"
    assert getattr(task_func, "job_timeout", -1) is None, "job_timeout deve ser explicitamente None (infinito)"

    # 2. Verifica no WorkerSettings ARQ
    assert WorkerSettings.job_timeout is None, "WorkerSettings.job_timeout deve ser None"
    func_names = [f.name for f in WorkerSettings.functions]
    assert "execute_full_video_pipeline" in func_names
    for f in WorkerSettings.functions:
        if f.name == "execute_full_video_pipeline":
            assert f.timeout_s is None, "Timeout individual da função deve ser None (sem limite)"


def test_ensure_twenty_scenes_sequential_distribution():
    """Valida a Instrução 2: Garantia de exatamente 20 cenas (60s total, Parts 1, 2 e 3)."""
    # Teste com lista menor de cenas
    initial_scenes = [
        {"scene_number": 1, "narration": "Gancho inicial", "visual_prompt": "Cena 1", "on_screen_text": "GANCHO"},
        {"scene_number": 2, "narration": "Revelação do mistério", "visual_prompt": "Cena 2", "on_screen_text": "MISTÉRIO"},
    ]
    expanded = ensure_twenty_scenes(initial_scenes, "Narração completa de teste", "Pauta Dark")
    assert len(expanded) == 20, "O pipeline DEVE garantir exatamente 20 cenas"
    for idx, sc in enumerate(expanded):
        assert sc["scene_number"] == idx + 1
        assert sc["duration"] == 3.0
        assert sc["narration"]
        assert sc["visual_prompt"]


@pytest.mark.asyncio
async def test_full_media_pipeline_execution(tmp_path):
    """Valida execução completa garantindo 20 cenas, 60s de duração e compilação FFmpeg."""
    scenes = [
        {
            "scene_number": 1,
            "narration": "O mistério oculto nos confins do tempo.",
            "visual_prompt": "Ancient secret vault glowing in dark blue fog 9:16",
            "on_screen_text": "O MISTÉRIO OCULTO",
        },
        {
            "scene_number": 2,
            "narration": "Registros proibidos que agora vêm à tona.",
            "visual_prompt": "Classified documents burning with neon embers 9:16",
            "on_screen_text": "ARQUIVOS PROIBIDOS",
        },
    ]

    os.environ["ABVOS_DISABLE_EXTERNAL_IMAGE_API"] = "1"
    try:
        res = await execute_full_video_pipeline(
            business_id=9991,
            task_id=999888,
            scenes=scenes,
            full_narration="O mistério oculto nos confins do tempo. Registros proibidos que agora vêm à tona.",
        )

        assert res["success"] is True
        assert res["business_id"] == 9991
        assert res["task_id"] == 999888
        # 20 cenas garantidas
        assert res["scenes_count"] == 20
        assert len(res["images_generated"]) == 20

        # Validação do vídeo compilado
        assert Path(res["video"]["path"]).exists()
        assert res["video"]["resolution"] == "1080x1920"
        assert res["video"]["aspect_ratio"] == "9:16"
        assert res["video"]["duration_seconds"] == 60.0
        assert res["video"]["size_mb"] > 0

        # Validação dos assets
        assert Path(res["audio"]["path"]).exists()
        assert Path(res["subtitles"]["srt_path"]).exists()
        assert Path(res["subtitles"]["ass_path"]).exists()
    finally:
        os.environ.pop("ABVOS_DISABLE_EXTERNAL_IMAGE_API", None)
        shutil.rmtree(STORAGE_MEDIA_DIR / "biz_9991", ignore_errors=True)
        shutil.rmtree(STORAGE_OUTPUT_DIR / "biz_9991", ignore_errors=True)
