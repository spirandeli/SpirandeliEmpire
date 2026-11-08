import pytest
from pathlib import Path
from src.services.media.pipeline import execute_full_media_pipeline
from src.services.media.media_settings import get_ffmpeg_path, get_ffprobe_path


def test_ffmpeg_and_ffprobe_available():
    ffmpeg = get_ffmpeg_path()
    ffprobe = get_ffprobe_path()
    assert Path(ffmpeg).exists(), f"FFmpeg não encontrado em {ffmpeg}"
    assert Path(ffprobe).exists(), f"FFprobe não encontrado em {ffprobe}"


@pytest.mark.asyncio
async def test_full_media_pipeline_execution(tmp_path):
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

    res = await execute_full_media_pipeline(
        business_id=1,
        task_id=888,
        scenes=scenes,
        full_narration="O mistério oculto nos confins do tempo. Registros proibidos que agora vêm à tona.",
    )

    assert res["success"] is True
    assert res["business_id"] == 1
    assert res["task_id"] == 888
    assert res["scenes_count"] == 2
    assert Path(res["video"]["path"]).exists()
    assert res["video"]["resolution"] == "1080x1920"
    assert res["video"]["size_mb"] > 0
    assert Path(res["audio"]["path"]).exists()
    assert Path(res["subtitles"]["srt_path"]).exists()
    assert Path(res["subtitles"]["ass_path"]).exists()
