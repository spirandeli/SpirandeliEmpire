import logging
import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models import AgentLog, ApprovalQueue, Business, ContentAsset, Task, User
from src.services.media.agents.assembler_agent import AssemblerAgent
from src.services.media.agents.base import (
    AgentContext,
    load_manifest,
    save_manifest,
)
from src.services.media.agents.contracts import (
    STAGE_METADATA,
    STAGE_ORDER,
    AgentStage,
    PipelineManifest,
)
from src.services.media.agents.narration_agent import NarrationAgent
from src.services.media.agents.script_agent import ScriptAgent
from src.services.media.agents.subtitle_agent import SubtitleAgent
from src.services.media.agents.video_scene_agent import VideoSceneAgent

logger = logging.getLogger("abvos.media.agents.orchestrator")

STAGE_ACTION_MAP: Dict[str, AgentStage] = {
    "agent_script": AgentStage.SCRIPT,
    "agent_video_scenes": AgentStage.VIDEO_SCENES,
    "agent_narration": AgentStage.NARRATION,
    "agent_subtitles": AgentStage.SUBTITLES,
    "agent_assemble_video": AgentStage.ASSEMBLE,
}

STAGE_PROGRESS_BASE: Dict[str, float] = {
    AgentStage.SCRIPT.value: 0.0,
    AgentStage.VIDEO_SCENES.value: 20.0,
    AgentStage.NARRATION.value: 55.0,
    AgentStage.SUBTITLES.value: 75.0,
    AgentStage.ASSEMBLE.value: 85.0,
}

STAGE_PROGRESS_WEIGHT: Dict[str, float] = {
    AgentStage.SCRIPT.value: 20.0,
    AgentStage.VIDEO_SCENES.value: 35.0,
    AgentStage.NARRATION.value: 20.0,
    AgentStage.SUBTITLES.value: 10.0,
    AgentStage.ASSEMBLE.value: 15.0,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clean_parent_title(title: str) -> str:
    clean = (title or "Vídeo Dark").strip()
    for prefix in ("[Vídeo] ", "[Video] "):
        if clean.startswith(prefix):
            clean = clean[len(prefix):].strip()
    return clean


def _manifest_to_task_result(manifest: PipelineManifest, summary_override: Optional[str] = None) -> Dict[str, Any]:
    """Converte o PipelineManifest no formato compatível com Task.result e TaskMediaGallery.vue."""
    script = manifest.script
    scenes = script.scenes if script else []
    vb = script.visual_bible.model_dump() if script else {}

    items = [
        {
            "title": sc.on_screen_text or f"Cena {sc.scene_number:02d}",
            "description": f"{sc.camera_angle} ({sc.camera_motion}) · ~{sc.estimated_seconds}s",
            "script": sc.narration,
            "visual_prompt": sc.visual_prompt_en,
            "camera_motion": sc.camera_motion,
            "include_character": sc.include_character,
            "tags": ["multi_agente", sc.act],
        }
        for sc in scenes
    ]

    md_lines = []
    if script:
        md_lines.append(f"## {script.title}\n")
        if script.hook:
            md_lines.append(f"**Gancho (0-3s):** {script.hook}\n")
        md_lines.append(
            f"**Palavras:** {script.word_count} | **Duração estimada:** ~{script.estimated_total_seconds}s | **Estilo:** {vb.get('art_style', '')}\n"
        )
        for sc in scenes:
            md_lines.append(
                f"### Cena {sc.scene_number:02d} [{sc.act}] · `{sc.camera_motion}`\n"
                f"- **Fala:** {sc.narration}\n"
                f"- **Prompt Gemini:** `{sc.visual_prompt_en}`"
            )

    result: Dict[str, Any] = {
        "summary": summary_override or f"Pipeline Multi-Agente: {manifest.title} ({len(scenes)} cenas).",
        "deliverable_type": "dark_script",
        "markdown_content": "\n\n".join(md_lines),
        "visual_bible": vb,
        "items": items,
        "pipeline_manifest": manifest.model_dump(mode="json"),
        "stage_statuses": manifest.stage_statuses,
    }

    media_block: Dict[str, Any] = {
        "success": bool(manifest.final_video),
        "business_id": manifest.business_id,
        "task_id": manifest.task_id,
        "scenes_count": len(scenes),
        "visual_bible": vb,
    }
    if manifest.scenes_visual:
        media_block["images_generated"] = [a.url for a in manifest.scenes_visual.assets]
        media_block["scenes"] = [a.model_dump() for a in manifest.scenes_visual.assets]
    if manifest.narration:
        result["audio_url"] = manifest.narration.url
        media_block["audio"] = {
            "path": manifest.narration.master_audio_path,
            "url": manifest.narration.url,
            "duration_seconds": manifest.narration.total_duration_seconds,
            "provider": manifest.narration.provider,
        }
    if manifest.subtitles:
        result["srt_url"] = manifest.subtitles.srt_url
        media_block["subtitles"] = {
            "srt_path": manifest.subtitles.srt_path,
            "srt_url": manifest.subtitles.srt_url,
            "ass_path": manifest.subtitles.ass_path,
        }
    if manifest.final_video:
        result["video_url"] = manifest.final_video.url
        media_block["video"] = {
            "path": manifest.final_video.video_path,
            "url": manifest.final_video.url,
            "resolution": manifest.final_video.resolution,
            "aspect_ratio": manifest.final_video.aspect_ratio,
            "duration_seconds": manifest.final_video.duration_seconds,
            "size_mb": manifest.final_video.size_mb,
            "motion_applied": manifest.final_video.motion_applied,
            "ffprobe_verified": manifest.final_video.ffprobe_verified,
        }
        result["summary"] = (
            f"🎬 VÍDEO FINAL RENDERIZADO ({manifest.final_video.resolution} 9:16, "
            f"{manifest.final_video.duration_seconds}s, {manifest.final_video.size_mb}MB) via 5 Agentes Especializados."
        )

    result["media"] = media_block
    return result


class VideoOrchestrator:
    """
    Orquestrador Multi-Agente de Produção de Vídeo (5 Agentes Especializados):
    1. ScriptAgent (Roteiros Completos) -> pausa opcional em Supervisão Humana
    2. VideoSceneAgent (Geração de Cenas 9:16 via Google Gemini)
    3. NarrationAgent (Síntese de Voz PT-BR Natural + Word Timings)
    4. SubtitleAgent (Legendas Prosódicas .ass/.srt Word-Highlight)
    5. AssemblerAgent (Ken Burns + xfade + Queima de Legendas + FFprobe)
    """

    def __init__(self) -> None:
        self.script_agent = ScriptAgent()
        self.video_scene_agent = VideoSceneAgent()
        self.narration_agent = NarrationAgent()
        self.subtitle_agent = SubtitleAgent()
        self.assembler_agent = AssemblerAgent()

    async def ensure_stage_subtasks(self, db: AsyncSession, parent_task: Task) -> Dict[str, Task]:
        """
        Garante a criação das 5 subtarefas especializadas vinculadas à tarefa-pai via `parent_id`,
        aproveitando nativamente o agrupamento do Kanban em `TasksBoardView.vue`.
        """
        res = await db.execute(
            select(Task).where(
                Task.parent_id == parent_task.id,
                Task.deleted_at.is_(None),
            )
        )
        existing_children = res.scalars().all()
        by_stage: Dict[str, Task] = {}
        for ch in existing_children:
            st = (ch.payload or {}).get("pipeline_stage")
            if not st and ch.agent_action in STAGE_ACTION_MAP:
                st = STAGE_ACTION_MAP[ch.agent_action].value
            if st:
                by_stage[st] = ch

        base_title = _clean_parent_title(parent_task.title)
        now = _utc_now()

        for stage in STAGE_ORDER:
            if stage.value in by_stage:
                continue
            meta = STAGE_METADATA[stage.value]
            sub = Task(
                business_id=parent_task.business_id,
                user_id=parent_task.user_id,
                parent_id=parent_task.id,
                title=f"{base_title} - Parte {meta['order']}: {meta['label']}",
                description=meta["description"],
                assignee="agent",
                status="backlog",
                priority=parent_task.priority or "high",
                source="agent",
                position=meta["order"],
                agent_action=meta["agent_action"],
                payload={
                    "parent_task_id": parent_task.id,
                    "pipeline_stage": stage.value,
                    "stage_order": meta["order"],
                    "stage_short_label": meta["short_label"],
                    "video_progress": {
                        "stage": stage.value,
                        "percent": 0.0,
                        "status_log": "Aguardando etapa anterior...",
                        "updated_at": now.isoformat(),
                    },
                },
                status_log="Aguardando etapa anterior...",
                created_at=now,
                updated_at=now,
            )
            db.add(sub)
            await db.flush()
            by_stage[stage.value] = sub

        await db.commit()
        return by_stage

    async def build_context(
        self,
        db: AsyncSession,
        parent_task: Task,
        user: User,
        pause_after_script: Optional[bool] = None,
    ) -> AgentContext:
        from src.services.jeffrey_orchestrator import get_effective_gemini_key

        gemini_key = await get_effective_gemini_key(user, db)
        biz: Optional[Business] = parent_task.business
        if not biz and parent_task.business_id:
            b_res = await db.execute(select(Business).where(Business.id == parent_task.business_id))
            biz = b_res.scalar_one_or_none()

        payload = dict(parent_task.payload or {})
        linked_asset: Optional[ContentAsset] = None
        if payload.get("content_asset_id"):
            ca_res = await db.execute(
                select(ContentAsset).where(ContentAsset.id == int(payload["content_asset_id"]))
            )
            linked_asset = ca_res.scalar_one_or_none()

        ca_content = dict(linked_asset.content or {}) if linked_asset else {}
        if pause_after_script is None:
            pause_after_script = bool(payload.get("pause_after_script", True))

        return AgentContext(
            task_id=parent_task.id,
            business_id=parent_task.business_id or 0,
            user_id=user.id,
            title=_clean_parent_title(parent_task.title),
            topic=str(payload.get("topic") or payload.get("theme") or _clean_parent_title(parent_task.title)),
            context_text=str(
                (linked_asset.body if linked_asset and linked_asset.body else "")
                or payload.get("hook")
                or parent_task.description
                or parent_task.title
            ),
            business_name=biz.name if biz else "",
            business_niche=(biz.niche or "") if biz else "",
            business_archetype=(biz.archetype or "") if biz else "",
            brand_rules=dict(biz.brand_rules or {}) if (biz and biz.brand_rules) else {},
            format_type=str(ca_content.get("format_type") or payload.get("format_type") or "short"),
            target_platform=str((linked_asset.platform if linked_asset else None) or payload.get("platform") or "youtube_shorts"),
            tone=str(payload.get("tone") or "Envolvente, claro e cinematográfico"),
            visual_style=str(ca_content.get("visual_style") or payload.get("visual_style") or ""),
            voice_persona=str(ca_content.get("voice_persona") or payload.get("voice_persona") or ""),
            gemini_key=gemini_key or "",
            elevenlabs_key=str(payload.get("elevenlabs_key") or os.getenv("ELEVENLABS_API_KEY") or ""),
            pause_after_script=pause_after_script,
        )

    async def _sync_stage_status_to_db(
        self,
        db: AsyncSession,
        parent_task: Task,
        subtasks: Dict[str, Task],
        stage: str,
        status_val: str,
        percent: float,
        message: str,
        manifest: Optional[PipelineManifest] = None,
    ) -> None:
        now = _utc_now()
        sub = subtasks.get(stage)
        if sub:
            sub.status = status_val
            sub.status_log = message
            sub_payload = dict(sub.payload or {})
            sub_payload["video_progress"] = {
                "stage": stage,
                "percent": round(percent, 1),
                "status_log": message,
                "updated_at": now.isoformat(),
            }
            sub.payload = sub_payload
            sub.updated_at = now
            if status_val == "done":
                sub.completed_at = now
            elif status_val == "in_progress_agent" and not sub.started_at:
                sub.started_at = now
            if manifest:
                sub.result = self._extract_stage_result(stage, manifest)

        overall_pct = STAGE_PROGRESS_BASE.get(stage, 0.0) + (percent / 100.0) * STAGE_PROGRESS_WEIGHT.get(stage, 20.0)
        if stage == AgentStage.ASSEMBLE.value and status_val == "done":
            overall_pct = 100.0

        parent_task.status_log = message
        p_payload = dict(parent_task.payload or {})
        p_payload["video_progress"] = {
            "stage": stage,
            "percent": round(min(100.0, overall_pct), 1),
            "status_log": message,
            "updated_at": now.isoformat(),
        }
        if manifest:
            p_payload["stage_statuses"] = dict(manifest.stage_statuses)
        parent_task.payload = p_payload
        parent_task.updated_at = now
        await db.commit()

    def _extract_stage_result(self, stage: str, manifest: PipelineManifest) -> Dict[str, Any]:
        if stage == AgentStage.SCRIPT.value and manifest.script:
            return {
                "summary": f"Roteiro completo com {len(manifest.script.scenes)} cenas ({manifest.script.word_count} palavras).",
                "visual_bible": manifest.script.visual_bible.model_dump(),
                "items": [
                    {
                        "title": sc.on_screen_text or f"Cena {sc.scene_number:02d}",
                        "description": f"{sc.camera_angle} · {sc.camera_motion}",
                        "script": sc.narration,
                        "visual_prompt": sc.visual_prompt_en,
                        "tags": [sc.act, sc.camera_motion],
                    }
                    for sc in manifest.script.scenes
                ],
            }
        if stage == AgentStage.VIDEO_SCENES.value and manifest.scenes_visual:
            return {
                "summary": f"{manifest.scenes_visual.total_scenes} cenas geradas (provedor principal: {manifest.scenes_visual.provider_primary}).",
                "media": {"images_generated": [a.url for a in manifest.scenes_visual.assets], "scenes": [a.model_dump() for a in manifest.scenes_visual.assets]},
            }
        if stage == AgentStage.NARRATION.value and manifest.narration:
            return {
                "summary": f"Narração master ({manifest.narration.total_duration_seconds}s, {manifest.narration.provider}, rate={manifest.narration.rate_used}).",
                "audio_url": manifest.narration.url,
                "media": {"audio": {"url": manifest.narration.url, "duration_seconds": manifest.narration.total_duration_seconds, "provider": manifest.narration.provider}},
            }
        if stage == AgentStage.SUBTITLES.value and manifest.subtitles:
            return {
                "summary": f"Legendas sincronizadas ({manifest.subtitles.chunks_count} blocos, preset={manifest.subtitles.style_preset}).",
                "srt_url": manifest.subtitles.srt_url,
                "media": {"subtitles": {"srt_url": manifest.subtitles.srt_url, "ass_path": manifest.subtitles.ass_path}},
            }
        if stage == AgentStage.ASSEMBLE.value and manifest.final_video:
            return _manifest_to_task_result(manifest)
        return {}

    async def _sync_script_to_content_and_approval(
        self,
        db: AsyncSession,
        parent_task: Task,
        user: User,
        manifest: PipelineManifest,
        await_human_approval: bool,
    ) -> None:
        if not manifest.script:
            return
        now = _utc_now()
        payload = dict(parent_task.payload or {})
        ca_id = payload.get("content_asset_id")
        asset: Optional[ContentAsset] = None
        if ca_id:
            ca_res = await db.execute(select(ContentAsset).where(ContentAsset.id == int(ca_id)))
            asset = ca_res.scalar_one_or_none()

        scenes_dicts = [
            {
                "scene_number": sc.scene_number,
                "act": sc.act,
                "narration": sc.narration,
                "visual_prompt": sc.visual_prompt_en,
                "include_character": sc.include_character,
                "camera_angle": sc.camera_angle,
                "camera_motion": sc.camera_motion,
                "estimated_seconds": sc.estimated_seconds,
                "on_screen_text": sc.on_screen_text,
            }
            for sc in manifest.script.scenes
        ]
        vb_dict = manifest.script.visual_bible.model_dump()

        if asset:
            ca_content = dict(asset.content or {})
            ca_content.update({
                "hook": manifest.script.hook,
                "cta": manifest.script.cta,
                "scenes": scenes_dicts,
                "visual_bible": vb_dict,
                "seo_tags": manifest.script.seo_tags,
                "task_id": parent_task.id,
            })
            if manifest.final_video:
                ca_content["video_url"] = manifest.final_video.url
            if manifest.narration:
                ca_content["audio_url"] = manifest.narration.url
            if manifest.subtitles:
                ca_content["srt_url"] = manifest.subtitles.srt_url
            asset.content = ca_content
            asset.body = manifest.script.full_narration
            asset.updated_at = now
        else:
            asset = ContentAsset(
                tracking_code=f"DARK-{parent_task.business_id}-{parent_task.id}-{secrets.token_hex(3).upper()}",
                business_id=parent_task.business_id,
                type="dark_script_short" if manifest.script.format_type == "short" else "dark_script_long",
                platform=manifest.script.target_platform,
                title=manifest.script.title,
                body=manifest.script.full_narration,
                content={
                    "hook": manifest.script.hook,
                    "cta": manifest.script.cta,
                    "scenes": scenes_dicts,
                    "visual_bible": vb_dict,
                    "seo_tags": manifest.script.seo_tags,
                    "format_type": manifest.script.format_type,
                    "voice_persona": manifest.script.voice_persona,
                    "task_id": parent_task.id,
                },
                status="supervision" if await_human_approval else "approved",
                created_at=now,
                updated_at=now,
            )
            db.add(asset)
            await db.flush()
            payload["content_asset_id"] = asset.id
            parent_task.payload = payload

        if await_human_approval:
            # Garante item pendente na ApprovalQueue vinculado à task-pai
            ap_res = await db.execute(
                select(ApprovalQueue).where(
                    ApprovalQueue.task_id == parent_task.id,
                    ApprovalQueue.status == "pending",
                )
            )
            existing_appr = ap_res.scalar_one_or_none()
            appr_payload = {
                "content_asset_id": asset.id,
                "task_id": parent_task.id,
                "pipeline_pause_stage": "script",
                "hook": manifest.script.hook,
                "scenes_count": len(scenes_dicts),
                "scenes": scenes_dicts,
                "visual_bible": vb_dict,
                "word_count": manifest.script.word_count,
                "estimated_total_seconds": manifest.script.estimated_total_seconds,
            }
            if existing_appr:
                existing_appr.payload = appr_payload
                existing_appr.summary = f"Roteiro ({len(scenes_dicts)} cenas, {manifest.script.word_count} palavras) pronto para aprovação antes da mídia."
                existing_appr.updated_at = now
            else:
                appr = ApprovalQueue(
                    business_id=parent_task.business_id or 0,
                    user_id=user.id,
                    task_id=parent_task.id,
                    type="dark_script_approval",
                    title=f"Revisar Roteiro (Agente 1): {manifest.script.title}",
                    summary=f"Roteiro ({len(scenes_dicts)} cenas, ~{manifest.script.estimated_total_seconds}s) aguardando aprovação para liberar Geração de Cenas, Narração, Legendas e Montagem.",
                    payload=appr_payload,
                    status="pending",
                    priority=parent_task.priority or "high",
                    agent_confidence=Decimal("0.95"),
                    created_at=now,
                    updated_at=now,
                )
                db.add(appr)
                await db.flush()
                asset.approval_queue_id = appr.id

    async def run_pipeline(
        self,
        db: AsyncSession,
        parent_task: Task,
        user: User,
        preexisting_scenes: Optional[List[Dict[str, Any]]] = None,
        preexisting_bible: Optional[Dict[str, Any]] = None,
        pause_after_script: Optional[bool] = None,
        start_from_stage: AgentStage = AgentStage.SCRIPT,
        force_regenerate: bool = False,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executa a orquestração multi-agente para uma tarefa de vídeo:
        - Cria as 5 subtarefas agrupadas no Kanban (`parent_id = parent_task.id`);
        - Se `pause_after_script=True` e o roteiro ainda não foi aprovado, pausa em `awaiting_supervision`
          após o Agente 1 para revisão humana antes de gerar imagens/áudio/vídeo;
        - Quando aprovado (ou `pause_after_script=False`), executa Agentes 2 -> 3 -> 4 -> 5.
        """
        ctx = await self.build_context(db, parent_task, user, pause_after_script=pause_after_script)
        subtasks = await self.ensure_stage_subtasks(db, parent_task)
        manifest = load_manifest(ctx)

        payload = dict(parent_task.payload or {})
        script_approved = bool(payload.get("script_approved", False))

        # Extrai cenas pré-existentes do ContentAsset caso ainda não estejam no manifest
        if not preexisting_scenes and payload.get("content_asset_id"):
            ca_res = await db.execute(select(ContentAsset).where(ContentAsset.id == int(payload["content_asset_id"])))
            ca = ca_res.scalar_one_or_none()
            if ca and isinstance(ca.content, dict) and ca.content.get("scenes"):
                preexisting_scenes = list(ca.content["scenes"])
                if not preexisting_bible and isinstance(ca.content.get("visual_bible"), dict):
                    preexisting_bible = dict(ca.content["visual_bible"])

        async def _progress_hook(stage_name: str, pct: float, msg: str) -> None:
            await self._sync_stage_status_to_db(
                db=db,
                parent_task=parent_task,
                subtasks=subtasks,
                stage=stage_name,
                status_val="in_progress_agent",
                percent=pct,
                message=msg,
                manifest=manifest,
            )

        ctx.progress_cb = _progress_hook

        parent_task.status = "in_progress_agent"
        parent_task.failure_reason = None
        if not parent_task.started_at:
            parent_task.started_at = _utc_now()
        await db.commit()

        # ETAPA 1: Agente de Roteiros Completos
        if start_from_stage == AgentStage.SCRIPT:
            manifest = await self.script_agent.run(
                ctx=ctx,
                manifest=manifest,
                preexisting_scenes=preexisting_scenes,
                preexisting_bible=preexisting_bible,
                feedback=feedback,
                force_regenerate=force_regenerate,
            )
            save_manifest(ctx, manifest)

            if ctx.pause_after_script and not script_approved:
                await self._sync_stage_status_to_db(
                    db=db,
                    parent_task=parent_task,
                    subtasks=subtasks,
                    stage=AgentStage.SCRIPT.value,
                    status_val="awaiting_supervision",
                    percent=100.0,
                    message="Roteiro pronto! Revise as falas e prompts antes de gerar imagens e áudio.",
                    manifest=manifest,
                )
                await self._sync_script_to_content_and_approval(
                    db=db,
                    parent_task=parent_task,
                    user=user,
                    manifest=manifest,
                    await_human_approval=True,
                )
                parent_task.status = "awaiting_supervision"
                parent_task.status_log = "Aguardando aprovação do Roteiro (Agente 1) para gerar mídia (20%)"
                parent_task.result = _manifest_to_task_result(
                    manifest,
                    summary_override=f"Agente 1 (Roteiro) concluído ({len(manifest.script.scenes)} cenas, ~{manifest.script.estimated_total_seconds}s). Aguardando sua aprovação para iniciar Agentes 2 a 5.",
                )
                db.add(
                    AgentLog(
                        user_id=user.id,
                        business_id=parent_task.business_id,
                        task_id=parent_task.id,
                        level="info",
                        event="agent_script_awaiting_approval",
                        message=f"Agente 1 finalizou o roteiro da Tarefa #{parent_task.id} e pausou para supervisão.",
                        context={"scenes_count": len(manifest.script.scenes)},
                        created_at=_utc_now(),
                    )
                )
                await db.commit()
                await db.refresh(parent_task)
                return {
                    "success": True,
                    "paused_for_approval": True,
                    "task_id": parent_task.id,
                    "status": parent_task.status,
                    "manifest": manifest.model_dump(mode="json"),
                    "result": parent_task.result,
                }

            await self._sync_stage_status_to_db(
                db=db,
                parent_task=parent_task,
                subtasks=subtasks,
                stage=AgentStage.SCRIPT.value,
                status_val="done",
                percent=100.0,
                message="Agente 1 (Roteiro) aprovado.",
                manifest=manifest,
            )

        # ETAPAS 2 a 5
        stage_idx_start = STAGE_ORDER.index(start_from_stage)
        for st in STAGE_ORDER[max(1, stage_idx_start):]:
            force_this = force_regenerate and (st == start_from_stage or st in (AgentStage.SUBTITLES, AgentStage.ASSEMBLE))
            if st == AgentStage.VIDEO_SCENES:
                manifest = await self.video_scene_agent.run(ctx, manifest, force_regenerate=force_this)
            elif st == AgentStage.NARRATION:
                manifest = await self.narration_agent.run(ctx, manifest, force_regenerate=force_this)
            elif st == AgentStage.SUBTITLES:
                manifest = await self.subtitle_agent.run(ctx, manifest, force_regenerate=force_this)
            elif st == AgentStage.ASSEMBLE:
                manifest = await self.assembler_agent.run(ctx, manifest, force_regenerate=force_this)

            save_manifest(ctx, manifest)
            await self._sync_stage_status_to_db(
                db=db,
                parent_task=parent_task,
                subtasks=subtasks,
                stage=st.value,
                status_val="done",
                percent=100.0,
                message=f"{STAGE_METADATA[st.value]['label']} concluído.",
                manifest=manifest,
            )

        await self._sync_script_to_content_and_approval(
            db=db,
            parent_task=parent_task,
            user=user,
            manifest=manifest,
            await_human_approval=False,
        )

        # Registra ContentAsset do vídeo final renderizado
        if manifest.final_video:
            vid_asset = ContentAsset(
                tracking_code=f"VID-{parent_task.business_id}-{parent_task.id}-{secrets.token_hex(3)}",
                business_id=parent_task.business_id,
                type="rendered_dark_video",
                platform=manifest.script.target_platform if manifest.script else "youtube_shorts",
                title=f"[Vídeo 9:16] {manifest.title}",
                body=manifest.final_video.url,
                content={
                    "video": manifest.final_video.model_dump(),
                    "audio": manifest.narration.model_dump(exclude={"word_timings", "segments"}) if manifest.narration else {},
                    "subtitles": manifest.subtitles.model_dump() if manifest.subtitles else {},
                    "scenes_count": len(manifest.script.scenes) if manifest.script else 0,
                    "format_type": "short_9x16",
                },
                status="pending_approval",
                created_at=_utc_now(),
            )
            db.add(vid_asset)

        final_result = _manifest_to_task_result(manifest)
        parent_task.result = final_result
        parent_task.status = "done"
        parent_task.status_log = "Concluído via 5 Agentes Especializados (100%)"
        parent_task.completed_at = _utc_now()
        parent_task.updated_at = _utc_now()

        p_payload = dict(parent_task.payload or {})
        p_payload["script_approved"] = True
        p_payload["video_progress"] = {
            "stage": "done",
            "percent": 100.0,
            "status_log": parent_task.status_log,
            "output_path": "/app/storage/output/",
            "updated_at": _utc_now().isoformat(),
        }
        parent_task.payload = p_payload

        db.add(
            AgentLog(
                user_id=user.id,
                business_id=parent_task.business_id,
                task_id=parent_task.id,
                level="info",
                event="multi_agent_video_completed",
                message=f"Pipeline de 5 agentes concluído para Tarefa #{parent_task.id}: {manifest.final_video.url if manifest.final_video else ''}",
                context={"task_id": parent_task.id},
                created_at=_utc_now(),
            )
        )
        await db.commit()
        await db.refresh(parent_task)

        return {
            "success": True,
            "paused_for_approval": False,
            "task_id": parent_task.id,
            "status": parent_task.status,
            "manifest": manifest.model_dump(mode="json"),
            "result": final_result,
        }

    async def run_single_stage(
        self,
        db: AsyncSession,
        parent_task: Task,
        user: User,
        stage: AgentStage,
        cascade: bool = True,
        feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Re-executa um agente específico (e opcionalmente seus dependentes a jusante)."""
        if stage == AgentStage.SCRIPT:
            payload = dict(parent_task.payload or {})
            payload["script_approved"] = False if not cascade else True
            parent_task.payload = payload
            await db.commit()
            return await self.run_pipeline(
                db=db,
                parent_task=parent_task,
                user=user,
                pause_after_script=not cascade,
                start_from_stage=AgentStage.SCRIPT,
                force_regenerate=True,
                feedback=feedback,
            )

        ctx = await self.build_context(db, parent_task, user, pause_after_script=False)
        subtasks = await self.ensure_stage_subtasks(db, parent_task)
        manifest = load_manifest(ctx)

        if stage == AgentStage.VIDEO_SCENES:
            manifest = await self.video_scene_agent.run(ctx, manifest, force_regenerate=True)
            save_manifest(ctx, manifest)
            await self._sync_stage_status_to_db(db, parent_task, subtasks, stage.value, "done", 100.0, "Cenas regeneradas.", manifest)
            if cascade and manifest.narration and manifest.subtitles:
                manifest = await self.assembler_agent.run(ctx, manifest, force_regenerate=True)
                save_manifest(ctx, manifest)
                await self._sync_stage_status_to_db(db, parent_task, subtasks, AgentStage.ASSEMBLE.value, "done", 100.0, "Vídeo remontado.", manifest)
        elif stage == AgentStage.NARRATION:
            manifest = await self.narration_agent.run(ctx, manifest, force_regenerate=True)
            save_manifest(ctx, manifest)
            await self._sync_stage_status_to_db(db, parent_task, subtasks, stage.value, "done", 100.0, "Narração regenerada.", manifest)
            if cascade:
                manifest = await self.subtitle_agent.run(ctx, manifest, force_regenerate=True)
                save_manifest(ctx, manifest)
                await self._sync_stage_status_to_db(db, parent_task, subtasks, AgentStage.SUBTITLES.value, "done", 100.0, "Legendas ressincronizadas.", manifest)
                if manifest.scenes_visual:
                    manifest = await self.assembler_agent.run(ctx, manifest, force_regenerate=True)
                    save_manifest(ctx, manifest)
                    await self._sync_stage_status_to_db(db, parent_task, subtasks, AgentStage.ASSEMBLE.value, "done", 100.0, "Vídeo remontado.", manifest)
        elif stage == AgentStage.SUBTITLES:
            manifest = await self.subtitle_agent.run(ctx, manifest, force_regenerate=True)
            save_manifest(ctx, manifest)
            await self._sync_stage_status_to_db(db, parent_task, subtasks, stage.value, "done", 100.0, "Legendas regeneradas.", manifest)
            if cascade and manifest.scenes_visual and manifest.narration:
                manifest = await self.assembler_agent.run(ctx, manifest, force_regenerate=True)
                save_manifest(ctx, manifest)
                await self._sync_stage_status_to_db(db, parent_task, subtasks, AgentStage.ASSEMBLE.value, "done", 100.0, "Vídeo remontado.", manifest)
        elif stage == AgentStage.ASSEMBLE:
            manifest = await self.assembler_agent.run(ctx, manifest, force_regenerate=True)
            save_manifest(ctx, manifest)
            await self._sync_stage_status_to_db(db, parent_task, subtasks, stage.value, "done", 100.0, "Vídeo remontado.", manifest)

        parent_task.result = _manifest_to_task_result(manifest)
        if manifest.final_video:
            parent_task.status = "done"
        parent_task.updated_at = _utc_now()
        await db.commit()
        await db.refresh(parent_task)
        return {
            "success": True,
            "task_id": parent_task.id,
            "stage": stage.value,
            "manifest": manifest.model_dump(mode="json"),
            "result": parent_task.result,
        }

    async def regenerate_scene(
        self,
        db: AsyncSession,
        parent_task: Task,
        user: User,
        scene_number: int,
        custom_prompt: Optional[str] = None,
        reassemble: bool = False,
    ) -> Dict[str, Any]:
        ctx = await self.build_context(db, parent_task, user, pause_after_script=False)
        subtasks = await self.ensure_stage_subtasks(db, parent_task)
        manifest = load_manifest(ctx)
        manifest = await self.video_scene_agent.regenerate_single_scene(
            ctx=ctx,
            manifest=manifest,
            scene_number=scene_number,
            custom_prompt=custom_prompt,
        )
        save_manifest(ctx, manifest)
        await self._sync_stage_status_to_db(
            db, parent_task, subtasks, AgentStage.VIDEO_SCENES.value, "done", 100.0,
            f"Cena #{scene_number} regenerada via Gemini.", manifest
        )
        if reassemble and manifest.narration and manifest.subtitles:
            manifest = await self.assembler_agent.run(ctx, manifest, force_regenerate=True)
            save_manifest(ctx, manifest)
            await self._sync_stage_status_to_db(
                db, parent_task, subtasks, AgentStage.ASSEMBLE.value, "done", 100.0,
                "Vídeo remontado após troca de cena.", manifest
            )
        parent_task.result = _manifest_to_task_result(manifest)
        parent_task.updated_at = _utc_now()
        await db.commit()
        return {
            "success": True,
            "task_id": parent_task.id,
            "scene_number": scene_number,
            "manifest": manifest.model_dump(mode="json"),
            "result": parent_task.result,
        }

