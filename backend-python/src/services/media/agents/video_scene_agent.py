import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.services.media.agents.base import AgentContext, BaseMediaAgent
from src.services.media.agents.contracts import (
    AgentStage,
    PipelineManifest,
    ScenesArtifact,
    SceneVisualAsset,
    ScriptSceneSpec,
)
from src.services.media.image_service import generate_scene_image_detailed

logger = logging.getLogger("abvos.media.agents.video_scenes")


class VideoSceneAgent(BaseMediaAgent):
    """
    Agente 2 — Geração de Vídeo & Cenas Visuais:
    Utiliza Google Gemini (Gemini Flash Image / Imagen 3) como motor primário 9:16,
    aplica a Bíblia Visual do Roteirista de forma contextual (sem forçar rosto em planos de detalhe)
    e prepara metadados de movimento de câmera (Ken Burns) para o Montador.
    """

    stage = AgentStage.VIDEO_SCENES

    async def _vision_quality_check(
        self,
        image_path: str,
        scene: ScriptSceneSpec,
        gemini_key: str,
    ) -> tuple[bool, str]:
        """
        Inspeção leve via Gemini Vision (opcional) para detectar texto indesejado na imagem
        ou desvios grotescos da cena antes de aprovar o frame.
        """
        if not gemini_key or os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") == "1":
            return True, ""
        if os.getenv("ABVOS_ENABLE_VISION_CRITIC", "0") != "1":
            return True, ""

        try:
            from google import genai
            from google.genai import types

            img_bytes = Path(image_path).read_bytes()

            def _call() -> str:
                client = genai.Client(api_key=gemini_key)
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                        (
                            f"Evaluate this 9:16 scene image for prompt: '{scene.visual_prompt_en[:220]}'. "
                            "Reply ONLY valid JSON: {\"ok\": true/false, \"reason\": \"short reason\"}. "
                            "Mark ok=false ONLY if there is obvious garbled overlaid text, split-screen collage, or completely blank/corrupted frame."
                        ),
                    ],
                )
                return getattr(resp, "text", "") or ""

            loop = asyncio.get_running_loop()
            raw = await asyncio.wait_for(loop.run_in_executor(None, _call), timeout=15.0)
            cleaned = raw.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()
            parsed = json.loads(cleaned)
            return bool(parsed.get("ok", True)), str(parsed.get("reason") or "")
        except Exception as exc:
            logger.debug(f"[VideoSceneAgent] Vision check ignorado na cena {scene.scene_number}: {exc}")
            return True, ""

    async def _generate_scene_asset(
        self,
        ctx: AgentContext,
        scene: ScriptSceneSpec,
        visual_bible_dict: Dict[str, str],
        story_seed: int,
        scenes_dir: Path,
        custom_prompt: Optional[str] = None,
    ) -> SceneVisualAsset:
        target_file = str(scenes_dir / f"scene_{scene.scene_number:02d}.jpg")
        prompt_to_use = (custom_prompt or scene.visual_prompt_en or "").strip()
        clean_key = (ctx.gemini_key or os.getenv("GEMINI_API_KEY", "")).strip()
        allow_secondary = os.getenv("ABVOS_ALLOW_SECONDARY_IMAGE_PROVIDERS", "0") == "1"
        prefer_gemini_only = bool(clean_key) and not allow_secondary and os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") != "1"

        res = await generate_scene_image_detailed(
            prompt=prompt_to_use,
            output_path=target_file,
            gemini_key=clean_key,
            scene_number=scene.scene_number,
            title=scene.on_screen_text or f"Cena {scene.scene_number}",
            max_retries=3,
            timeout_per_attempt=40.0,
            visual_bible=visual_bible_dict,
            story_seed=story_seed,
            include_character=scene.include_character,
            prefer_gemini_only=prefer_gemini_only,
        )

        # Se o usuário configurou Gemini explicitamente e todas as tentativas online falharam para esta cena,
        # verificamos se caiu no backdrop offline — se não estivermos em modo teste offline, registramos aviso.
        if prefer_gemini_only and res.get("fallback"):
            logger.warning(
                f"[VideoSceneAgent] Cena #{scene.scene_number}: Gemini Image indisponível no momento; "
                "usando backdrop de segurança para não bloquear o vídeo."
            )

        regen_count = 0
        ok_vision, reason = await self._vision_quality_check(target_file, scene, clean_key)
        if not ok_vision and clean_key:
            logger.info(f"[VideoSceneAgent] Cena #{scene.scene_number} reprovada no Vision Critic ({reason}); regenerando...")
            stricter_prompt = f"{prompt_to_use}, strictly no text, no letters, single unified cinematic frame"
            res = await generate_scene_image_detailed(
                prompt=stricter_prompt,
                output_path=target_file,
                gemini_key=clean_key,
                scene_number=scene.scene_number,
                title=scene.on_screen_text or f"Cena {scene.scene_number}",
                max_retries=2,
                timeout_per_attempt=40.0,
                visual_bible=visual_bible_dict,
                story_seed=story_seed + 97,
                include_character=scene.include_character,
                prefer_gemini_only=prefer_gemini_only,
            )
            regen_count = 1

        rel_url = f"/api/media/file/biz_{ctx.business_id}/task_{ctx.task_id}/scenes/scene_{scene.scene_number:02d}.jpg"
        return SceneVisualAsset(
            scene_number=scene.scene_number,
            asset_type="image",
            file_path=target_file,
            url=rel_url,
            width=1080,
            height=1920,
            provider=str(res.get("provider") or "google_gemini"),
            camera_motion=scene.camera_motion,
            include_character=scene.include_character,
            vision_verified=ok_vision,
            regenerated_count=regen_count,
        )

    async def regenerate_single_scene(
        self,
        ctx: AgentContext,
        manifest: PipelineManifest,
        scene_number: int,
        custom_prompt: Optional[str] = None,
    ) -> PipelineManifest:
        """Regenera apenas uma cena específica sem refazer as demais cenas do vídeo."""
        if not manifest.script:
            raise ValueError("Roteiro (Agente 1) precisa existir antes de regenerar uma cena.")

        target_scene = next(
            (sc for sc in manifest.script.scenes if sc.scene_number == scene_number),
            None,
        )
        if not target_scene:
            raise ValueError(f"Cena #{scene_number} não encontrada no roteiro.")

        if custom_prompt:
            target_scene.visual_prompt_en = custom_prompt.strip()

        scenes_dir = ctx.media_dir / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        vb_dict = manifest.script.visual_bible.model_dump()
        story_seed = (
            manifest.scenes_visual.story_seed
            if manifest.scenes_visual
            else 100000 + ((int(ctx.task_id or 1) * 7919) % 800000)
        )

        new_asset = await self._generate_scene_asset(
            ctx=ctx,
            scene=target_scene,
            visual_bible_dict=vb_dict,
            story_seed=story_seed,
            scenes_dir=scenes_dir,
            custom_prompt=custom_prompt,
        )

        existing_assets = list(manifest.scenes_visual.assets) if manifest.scenes_visual else []
        updated_assets = [a for a in existing_assets if a.scene_number != scene_number]
        updated_assets.append(new_asset)
        updated_assets.sort(key=lambda a: a.scene_number)

        manifest.scenes_visual = ScenesArtifact(
            assets=updated_assets,
            provider_primary="google_gemini",
            story_seed=story_seed,
            total_scenes=len(updated_assets),
        )
        manifest.stage_statuses[self.stage.value] = "completed"
        return manifest

    async def run(
        self,
        ctx: AgentContext,
        manifest: PipelineManifest,
        force_regenerate: bool = False,
    ) -> PipelineManifest:
        if not manifest.script or not manifest.script.scenes:
            raise ValueError("Agente 2 (Vídeo/Cenas) requer o artefato do Agente 1 (Roteiros).")

        scenes = manifest.script.scenes
        total = len(scenes)
        scenes_dir = ctx.media_dir / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)

        if (
            not force_regenerate
            and manifest.scenes_visual
            and len(manifest.scenes_visual.assets) == total
            and all(Path(a.file_path).exists() and Path(a.file_path).stat().st_size > 0 for a in manifest.scenes_visual.assets)
        ):
            manifest.stage_statuses[self.stage.value] = "completed"
            await self.notify(ctx, 100.0, f"Agente 2 (Vídeo/Cenas): {total} cenas reaproveitadas do cache.")
            return manifest

        story_seed = 100000 + ((int(ctx.task_id or 1) * 7919) % 800000)
        vb_dict = manifest.script.visual_bible.model_dump()
        assets: List[SceneVisualAsset] = []

        await self.notify(ctx, 2.0, f"Agente 2 (Vídeo/Cenas): Gerando {total} cenas 9:16 via Google Gemini...")
        for idx, sc in enumerate(scenes, start=1):
            asset = await self._generate_scene_asset(
                ctx=ctx,
                scene=sc,
                visual_bible_dict=vb_dict,
                story_seed=story_seed,
                scenes_dir=scenes_dir,
            )
            assets.append(asset)
            pct = round((idx / max(1, total)) * 100.0, 1)
            await self.notify(ctx, pct, f"Agente 2 (Vídeo/Cenas): Cena {idx}/{total} gerada ({asset.provider}).")

        manifest.scenes_visual = ScenesArtifact(
            assets=assets,
            provider_primary="google_gemini",
            story_seed=story_seed,
            total_scenes=len(assets),
        )
        manifest.stage_statuses[self.stage.value] = "completed"
        return manifest

