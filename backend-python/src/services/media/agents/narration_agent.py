import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from src.services.media.agents.base import AgentContext, BaseMediaAgent
from src.services.media.agents.contracts import (
    AgentStage,
    NarrationArtifact,
    NarrationSegment,
    PipelineManifest,
)
from src.services.media.media_settings import get_ffmpeg_path
from src.services.media.tts_service import (
    DEFAULT_EDGE_VOICE_PT,
    get_audio_duration_seconds,
    normalize_ptbr_for_speech,
    synthesize_narration,
)

logger = logging.getLogger("abvos.media.agents.narration")

SCENE_BREATH_PAUSE_SECONDS = 0.18


async def _create_silence_mp3(ffmpeg: str, silence_path: str, duration_sec: float = SCENE_BREATH_PAUSE_SECONDS) -> float:
    """Gera um pequeno arquivo de silêncio MP3 para respiro natural entre cenas e retorna sua duração real."""
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{duration_sec:.3f}",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        silence_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    if os.path.exists(silence_path) and os.path.getsize(silence_path) > 0:
        return get_audio_duration_seconds(silence_path)
    return 0.0


async def _concat_and_master_audio(
    ffmpeg: str,
    segment_paths: List[str],
    silence_path: str,
    master_output_path: str,
) -> bool:
    """Concatena segmentos com respiro natural e aplica normalização EBU R128 (loudnorm)."""
    tmp_dir = Path(master_output_path).parent / "narration_segments"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    concat_txt = tmp_dir / "audio_concat.txt"

    use_silence = bool(silence_path and os.path.exists(silence_path) and os.path.getsize(silence_path) > 0)
    with open(concat_txt, "w", encoding="utf-8") as f:
        for idx, sp in enumerate(segment_paths):
            f.write(f"file '{os.path.abspath(sp)}'\n")
            if use_silence and idx < len(segment_paths) - 1:
                f.write(f"file '{os.path.abspath(silence_path)}'\n")

    cmd = [
        ffmpeg,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        master_output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning(f"[NarrationAgent] Concat com loudnorm falhou ({stderr.decode(errors='replace')[:180]}), tentando concat direto...")
        cmd_plain = [
            ffmpeg,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            master_output_path,
        ]
        proc2 = await asyncio.create_subprocess_exec(
            *cmd_plain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc2.communicate()
        return proc2.returncode == 0
    return os.path.exists(master_output_path) and os.path.getsize(master_output_path) > 0


class NarrationAgent(BaseMediaAgent):
    """
    Agente 3 — Geração de Narração:
    Sintetiza cada cena individualmente em velocidade natural (+4%), normaliza pronúncia PT-BR,
    extrai timestamps exatos por palavra (WordBoundary / ElevenLabs with-timestamps) e
    gera a faixa master normalizada com respiros naturais entre cenas.
    """

    stage = AgentStage.NARRATION

    async def run(
        self,
        ctx: AgentContext,
        manifest: PipelineManifest,
        force_regenerate: bool = False,
    ) -> PipelineManifest:
        if not manifest.script or not manifest.script.scenes:
            raise ValueError("Agente 3 (Narração) requer o artefato do Agente 1 (Roteiros).")

        master_audio_path = str(ctx.media_dir / "narration.mp3")
        if (
            not force_regenerate
            and manifest.narration
            and os.path.exists(manifest.narration.master_audio_path)
            and os.path.getsize(manifest.narration.master_audio_path) > 0
            and len(manifest.narration.scene_durations) == len(manifest.script.scenes)
        ):
            manifest.stage_statuses[self.stage.value] = "completed"
            await self.notify(ctx, 100.0, "Agente 3 (Narração): Áudio master reaproveitado do cache.")
            return manifest

        scenes = manifest.script.scenes
        total = len(scenes)
        seg_dir = ctx.media_dir / "narration_segments"
        seg_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg = get_ffmpeg_path()

        natural_rate = os.getenv("ABVOS_TTS_NATURAL_RATE", "+4%")
        preferred_voice = ctx.voice_persona or manifest.script.voice_persona or DEFAULT_EDGE_VOICE_PT

        await self.notify(ctx, 5.0, f"Agente 3 (Narração): Sintetizando {total} falas em velocidade natural ({natural_rate})...")

        segments: List[NarrationSegment] = []
        segment_paths: List[str] = []
        provider_used = "edge_tts"

        for idx, sc in enumerate(scenes, start=1):
            seg_path = str(seg_dir / f"seg_{idx:02d}.mp3")
            spoken_text = normalize_ptbr_for_speech(sc.speech_text_tts or sc.narration) or sc.narration
            tts_res = await synthesize_narration(
                text=spoken_text,
                output_path=seg_path,
                elevenlabs_key=ctx.elevenlabs_key,
                preferred_voice=preferred_voice,
                rate=natural_rate,
                normalize_ptbr=False,  # já normalizado acima
            )
            provider_used = tts_res.get("provider", provider_used)
            seg_dur = float(tts_res["duration_seconds"])
            seg_words = list(tts_res.get("word_timings") or [])

            segments.append(
                NarrationSegment(
                    scene_number=sc.scene_number,
                    audio_path=seg_path,
                    duration_seconds=seg_dur,
                    text_spoken=spoken_text,
                    word_timings=seg_words,
                )
            )
            segment_paths.append(seg_path)
            pct = round(5.0 + (idx / max(1, total)) * 80.0, 1)
            await self.notify(ctx, pct, f"Agente 3 (Narração): Fala {idx}/{total} sintetizada ({seg_dur:.2f}s).")

        silence_path = str(seg_dir / "pause_breath.mp3")
        real_pause_dur = 0.0
        if len(segment_paths) > 1 and os.path.exists(ffmpeg):
            real_pause_dur = await _create_silence_mp3(ffmpeg, silence_path, SCENE_BREATH_PAUSE_SECONDS)

        if len(segment_paths) == 1:
            import shutil
            shutil.copy2(segment_paths[0], master_audio_path)
        else:
            ok_concat = await _concat_and_master_audio(
                ffmpeg=ffmpeg,
                segment_paths=segment_paths,
                silence_path=silence_path,
                master_output_path=master_audio_path,
            )
            if not ok_concat:
                raise RuntimeError("Agente 3 falhou ao concatenar os segmentos de narração.")

        # Acumula word_timings e durações exatas por cena alinhadas ao master_audio_path
        all_word_timings: List[Dict[str, Any]] = []
        scene_durations: List[float] = []
        cursor_sec = 0.0

        for idx, seg in enumerate(segments):
            is_last = idx == len(segments) - 1
            pause_after = 0.25 if is_last else real_pause_dur
            scene_visual_dur = round(max(0.8, seg.duration_seconds + pause_after), 2)
            scene_durations.append(scene_visual_dur)

            for w_idx, w in enumerate(seg.word_timings):
                shifted = dict(w)
                shifted["start"] = round(cursor_sec + float(w.get("start", 0.0)), 3)
                shifted["end"] = round(cursor_sec + float(w.get("end", 0.0)), 3)
                shifted["scene_number"] = seg.scene_number
                # Garante separação estrita de legenda ao fim de cada cena
                if w_idx == len(seg.word_timings) - 1:
                    shifted["sentence_end"] = True
                all_word_timings.append(shifted)

            cursor_sec += seg.duration_seconds + (0.0 if is_last else real_pause_dur)

        master_duration = get_audio_duration_seconds(master_audio_path)
        rel_url = f"/outputs/biz_{ctx.business_id}/task_{ctx.task_id}/narration.mp3"

        manifest.narration = NarrationArtifact(
            master_audio_path=master_audio_path,
            url=rel_url,
            total_duration_seconds=master_duration,
            provider=provider_used,
            voice_id=preferred_voice,
            rate_used=natural_rate,
            segments=segments,
            word_timings=all_word_timings,
            scene_durations=scene_durations,
        )
        manifest.stage_statuses[self.stage.value] = "completed"
        await self.notify(
            ctx,
            100.0,
            f"Agente 3 (Narração): Master {master_duration:.2f}s ({provider_used}, {len(all_word_timings)} palavras sincronizadas).",
        )
        return manifest

