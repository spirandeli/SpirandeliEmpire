import logging
import os
import re
from typing import Any, Dict, List

from src.services.media.agents.base import AgentContext, BaseMediaAgent
from src.services.media.agents.contracts import (
    AgentStage,
    PipelineManifest,
    SubtitleArtifact,
)
from src.services.media.subtitle_service import generate_subtitles

logger = logging.getLogger("abvos.media.agents.subtitles")


def _parse_srt_ts_to_seconds(ts: str) -> float:
    m = re.match(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", ts.strip())
    if not m:
        return 0.0
    h, mn, s, ms = (int(x) for x in m.groups())
    return h * 3600 + mn * 60 + s + ms / 1000.0


def _validate_srt_monotonicity(srt_path: str) -> List[str]:
    warnings: List[str] = []
    if not os.path.exists(srt_path) or os.path.getsize(srt_path) == 0:
        return ["Arquivo SRT ausente ou vazio."]

    content = open(srt_path, "r", encoding="utf-8").read()
    prev_end = -0.01
    for line in content.splitlines():
        if "-->" in line:
            parts = line.split("-->")
            if len(parts) == 2:
                st = _parse_srt_ts_to_seconds(parts[0])
                en = _parse_srt_ts_to_seconds(parts[1])
                if en <= st:
                    warnings.append(f"Bloco SRT com duração inválida: {line}")
                if st < prev_end - 0.02:
                    warnings.append(f"Sobreposição SRT detectada em {line}")
                prev_end = en
    return warnings


class SubtitleAgent(BaseMediaAgent):
    """
    Agente 4 — Geração de Legenda:
    Combina os timestamps reais de palavra do Agente de Narração com o texto limpo
    do Agente de Roteiros, gerando legendas .srt e .ass com destaque palavra-a-palavra
    (Hormozi Karaoke) e validação estrita de monotonicidade.
    """

    stage = AgentStage.SUBTITLES

    async def run(
        self,
        ctx: AgentContext,
        manifest: PipelineManifest,
        style_preset: str = "hormozi_karaoke",
        force_regenerate: bool = False,
    ) -> PipelineManifest:
        if not manifest.script or not manifest.narration:
            raise ValueError("Agente 4 (Legendas) requer os artefatos dos Agentes 1 (Roteiro) e 3 (Narração).")

        srt_path = str(ctx.media_dir / "subtitles.srt")
        ass_path = str(ctx.media_dir / "subtitles.ass")

        if (
            not force_regenerate
            and manifest.subtitles
            and os.path.exists(srt_path)
            and os.path.exists(ass_path)
            and os.path.getsize(ass_path) > 0
        ):
            manifest.stage_statuses[self.stage.value] = "completed"
            await self.notify(ctx, 100.0, "Agente 4 (Legendas): Legendas reaproveitadas do cache.")
            return manifest

        await self.notify(ctx, 20.0, "Agente 4 (Legendas): Alinhando blocos prosódicos e destaque palavra-a-palavra...")

        scenes = manifest.script.scenes
        durations = manifest.narration.scene_durations
        scenes_timing: List[Dict[str, Any]] = []
        acc = 0.0
        for idx, sc in enumerate(scenes):
            dur = float(durations[idx]) if idx < len(durations) else float(sc.estimated_seconds or 3.0)
            scenes_timing.append({
                "scene_number": sc.scene_number,
                "text": sc.narration,
                "start": round(acc, 2),
                "end": round(acc + dur, 2),
                "duration": round(dur, 2),
            })
            acc += dur

        sub_res = generate_subtitles(
            scenes_timing=scenes_timing,
            output_srt_path=srt_path,
            output_ass_path=ass_path,
            word_timings=manifest.narration.word_timings,
            style_preset=style_preset,
        )

        sync_warnings = _validate_srt_monotonicity(srt_path)
        if sync_warnings:
            logger.warning(f"[SubtitleAgent] Avisos de validação SRT: {sync_warnings[:3]}")

        srt_url = f"/outputs/biz_{ctx.business_id}/task_{ctx.task_id}/subtitles.srt"
        manifest.subtitles = SubtitleArtifact(
            srt_path=srt_path,
            ass_path=ass_path,
            srt_url=srt_url,
            chunks_count=int(sub_res.get("chunks_count", 0)),
            events_count=int(sub_res.get("events_count", 0)),
            style_preset=style_preset,
            sync_warnings=sync_warnings,
        )
        manifest.stage_statuses[self.stage.value] = "completed"
        await self.notify(
            ctx,
            100.0,
            f"Agente 4 (Legendas): {manifest.subtitles.chunks_count} blocos e {manifest.subtitles.events_count} eventos sincronizados.",
        )
        return manifest

