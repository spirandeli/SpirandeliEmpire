import logging
import os
import shutil
from pathlib import Path
from typing import List

from src.services.media.agents.base import AgentContext, BaseMediaAgent
from src.services.media.agents.contracts import (
    AgentStage,
    FinalVideoArtifact,
    PipelineManifest,
)
from src.services.media.image_service import create_cinematic_dark_backdrop
from src.services.media.video_renderer import render_video_with_audio_and_subtitles

logger = logging.getLogger("abvos.media.agents.assembler")


class AssemblerAgent(BaseMediaAgent):
    """
    Agente 5 — Montador e Editor Final:
    Recebe as cenas visuais (Agente 2), a narração masterizada (Agente 3) e as legendas (Agente 4),
    aplica movimento cinematográfico Ken Burns + transições suaves xfade (sem música de fundo),
    queima as legendas em 1080x1920@30fps, audita via FFprobe e publica em /storage/output.
    """

    stage = AgentStage.ASSEMBLE

    async def run(
        self,
        ctx: AgentContext,
        manifest: PipelineManifest,
        enable_motion: bool = True,
        force_regenerate: bool = False,
    ) -> PipelineManifest:
        if not manifest.script or not manifest.scenes_visual or not manifest.narration or not manifest.subtitles:
            raise ValueError(
                "Agente 5 (Montagem) requer todos os artefatos anteriores (Roteiro, Vídeo/Cenas, Narração e Legendas)."
            )

        final_video_path = str(ctx.media_dir / f"video_dark_task_{ctx.task_id}.mp4")
        if (
            not force_regenerate
            and manifest.final_video
            and os.path.exists(manifest.final_video.video_path)
            and os.path.getsize(manifest.final_video.video_path) > 0
        ):
            manifest.stage_statuses[self.stage.value] = "completed"
            await self.notify(ctx, 100.0, "Agente 5 (Montagem): Vídeo final reaproveitado do cache.")
            return manifest

        await self.notify(ctx, 15.0, "Agente 5 (Montagem): Validando cenas, áudio e legendas no disco...")

        verified_images: List[str] = []
        camera_motions: List[str] = []
        assets_sorted = sorted(manifest.scenes_visual.assets, key=lambda a: a.scene_number)

        for idx, asset in enumerate(assets_sorted, start=1):
            img_path = Path(asset.file_path)
            if not img_path.exists() or img_path.stat().st_size == 0:
                logger.warning(f"[AssemblerAgent] Cena #{idx} ausente no disco. Gerando fallback de segurança.")
                fallback = create_cinematic_dark_backdrop(width=1080, height=1920, scene_number=idx)
                img_path.parent.mkdir(parents=True, exist_ok=True)
                fallback.save(str(img_path), "JPEG", quality=92)
            verified_images.append(str(img_path))
            camera_motions.append(asset.camera_motion or "zoom_in")

        audio_path = manifest.narration.master_audio_path
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise FileNotFoundError(f"Áudio master não encontrado em {audio_path}")

        ass_path = manifest.subtitles.ass_path
        srt_path = manifest.subtitles.srt_path
        scene_durations = list(manifest.narration.scene_durations)

        await self.notify(
            ctx,
            45.0,
            f"Agente 5 (Montagem): Aplicando Ken Burns + transições e queimando legendas ({len(verified_images)} cenas)...",
        )

        render_res = await render_video_with_audio_and_subtitles(
            image_paths=verified_images,
            audio_path=audio_path,
            output_video_path=final_video_path,
            subtitle_ass_path=ass_path,
            fps=30,
            width=1080,
            height=1920,
            scene_durations=scene_durations,
            camera_motions=camera_motions,
            enable_motion=enable_motion,
            normalize_audio=False,  # Narração já masterizada pelo NarrationAgent
        )

        await self.notify(ctx, 88.0, "Agente 5 (Montagem): Publicando artefatos finais em /app/storage/output/...")

        output_dir = ctx.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_video_file = output_dir / f"video_dark_task_{ctx.task_id}.mp4"
        output_audio_file = output_dir / "narration.mp3"
        output_srt_file = output_dir / "subtitles.srt"
        output_scenes_dir = output_dir / "scenes"
        output_scenes_dir.mkdir(parents=True, exist_ok=True)

        if os.path.exists(final_video_path):
            shutil.copy2(final_video_path, str(output_video_file))
        if os.path.exists(audio_path):
            shutil.copy2(audio_path, str(output_audio_file))
        if os.path.exists(srt_path):
            shutil.copy2(srt_path, str(output_srt_file))
        for v_img in verified_images:
            if os.path.exists(v_img):
                shutil.copy2(v_img, str(output_scenes_dir / Path(v_img).name))

        video_url = f"/outputs/biz_{ctx.business_id}/task_{ctx.task_id}/video_dark_task_{ctx.task_id}.mp4"
        manifest.final_video = FinalVideoArtifact(
            video_path=final_video_path,
            url=video_url,
            resolution=str(render_res.get("resolution", "1080x1920")),
            aspect_ratio="9:16",
            duration_seconds=float(render_res.get("duration_seconds", 0.0)),
            size_mb=float(render_res.get("size_mb", 0.0)),
            motion_applied=bool(render_res.get("motion_applied", False)),
            ffprobe_verified=bool(render_res.get("ffprobe_verified", False)),
        )
        manifest.stage_statuses[self.stage.value] = "completed"
        await self.notify(
            ctx,
            100.0,
            f"Agente 5 (Montagem): Vídeo final MP4 ({manifest.final_video.duration_seconds}s, {manifest.final_video.size_mb}MB) concluído!",
        )
        return manifest

