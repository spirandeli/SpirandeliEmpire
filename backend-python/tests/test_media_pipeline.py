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
from src.services.media.tts_service import _align_word_timings_with_punctuation
from src.services.media.subtitle_service import (
    _build_chunks_from_word_timings,
    compute_scene_timings_from_words,
)
from src.services.media.image_service import _build_styled_prompt
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
    """Valida a Instrução 2: Garantia de exatamente 20 cenas (60s total, Parts 1, 2 e 3) e continuidade visual (visual_bible)."""
    # Teste com lista menor de cenas
    initial_scenes = [
        {"scene_number": 1, "narration": "Nos reinos celestiais brilhava a criação", "visual_prompt": "Cena 1", "on_screen_text": "GANCHO"},
        {"scene_number": 2, "narration": "A queda do arcanjo Lúcifer nos céus", "visual_prompt": "Cena 2", "on_screen_text": "MISTÉRIO"},
    ]
    expanded = ensure_twenty_scenes(initial_scenes, "A queda do arcanjo Lúcifer nos reinos celestiais.", "A Queda de Lúcifer")
    assert len(expanded) == 20, "O pipeline DEVE garantir exatamente 20 cenas"

    first_bible = expanded[0].get("visual_bible")
    assert isinstance(first_bible, dict)
    protagonist = first_bible.get("protagonist_description", "")
    world = first_bible.get("world_setting", "")
    assert len(protagonist) > 25
    assert len(world) > 20

    for idx, sc in enumerate(expanded):
        assert sc["scene_number"] == idx + 1
        assert sc["duration"] == 3.0
        assert sc["narration"]
        assert sc["visual_prompt"]
        # Todas as 20 cenas devem conter exatamente a mesma descrição do protagonista e do mundo
        assert protagonist in sc["visual_prompt"], f"Cena {idx + 1} perdeu a âncora física do protagonista"
        assert world in sc["visual_prompt"], f"Cena {idx + 1} perdeu a âncora do universo da história"
        assert sc.get("visual_bible") == first_bible

    styled_1 = _build_styled_prompt(expanded[0]["visual_prompt"], visual_bible=first_bible)
    styled_15 = _build_styled_prompt(expanded[14]["visual_prompt"], visual_bible=first_bible)
    assert protagonist[:40] in styled_1
    assert protagonist[:40] in styled_15


def test_subtitle_sentence_boundaries_never_merge_across_sentences():
    """
    Garante que os eventos WordBoundary sem pontuação do Edge-TTS nunca juntem o fim de uma frase
    com o começo da frase seguinte (ex: proibindo 'COROS DO UNIVERSO ELE' ou 'SER OUSAVA PISAR MAS').
    """
    script = (
        "Sua voz era a harpa que rege os coros do universo. "
        "Ele caminhava onde nenhum outro ser ousava pisar. "
        "Mas a perfeição começou a alimentar um perigoso segredo."
    )
    words = [
        ("Sua", 0.05, 0.25), ("voz", 0.26, 0.50), ("era", 0.51, 0.70), ("a", 0.71, 0.80),
        ("harpa", 0.81, 1.15), ("que", 1.16, 1.30), ("rege", 1.31, 1.60), ("os", 1.61, 1.75),
        ("coros", 1.76, 2.10), ("do", 2.11, 2.25), ("universo", 2.26, 2.75),
        ("Ele", 3.05, 3.25), ("caminhava", 3.26, 3.75), ("onde", 3.76, 4.00), ("nenhum", 4.01, 4.35),
        ("outro", 4.36, 4.65), ("ser", 4.66, 4.90), ("ousava", 4.91, 5.30), ("pisar", 5.31, 5.75),
        ("Mas", 6.05, 6.25), ("a", 6.26, 6.35), ("perfeição", 6.36, 6.90), ("começou", 6.91, 7.35),
        ("a", 7.36, 7.45), ("alimentar", 7.46, 7.95), ("um", 7.96, 8.10), ("perigoso", 8.11, 8.55),
        ("segredo", 8.56, 9.05),
    ]
    raw_timings = [{"text": w, "start": s, "end": e} for w, s, e in words]
    aligned = _align_word_timings_with_punctuation(script, raw_timings)
    chunks = _build_chunks_from_word_timings(aligned, max_words=4)

    assert chunks[0]["start"] == 0.0, "O primeiro bloco de legenda deve iniciar em 0.0s"
    chunk_texts = [c["text"] for c in chunks]
    for text in chunk_texts:
        assert "UNIVERSO ELE" not in text, f"Fusão indevida entre frases detectada: {text}"
        assert "PISAR MAS" not in text, f"Fusão indevida entre frases detectada: {text}"


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
