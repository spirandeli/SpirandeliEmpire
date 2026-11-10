import json
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from google.genai import types

from src.models import (
    Business,
    ContentAsset,
    ApprovalQueue,
    Task,
    User,
)
from src.schemas.business import DarkScriptCreateRequest, DarkScriptResponse, DarkScriptScene
from src.services.gemini_service import get_user_gemini_client
from src.services.media.agents.base import AgentContext, load_manifest, save_manifest
from src.services.media.agents.contracts import AgentStage
from src.services.media.agents.orchestrator import VideoOrchestrator, _manifest_to_task_result
from src.services.media.agents.script_agent import ScriptAgent

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def generate_dark_script(
    db: AsyncSession,
    user: User,
    business: Business,
    req: DarkScriptCreateRequest,
) -> dict[str, Any]:
    """
    Gera um roteiro completo via Agente 1 (ScriptAgent) com ritmo oral natural,
    Bíblia Visual adaptativa ao tema, direção de câmera por cena e submete à
    fila de aprovação humana antes de liberar os Agentes 2 a 5.
    """
    from src.services.jeffrey_orchestrator import get_effective_gemini_key

    now = _utc_now()
    is_short = req.format_type == "short" or req.target_platform in ("youtube_shorts", "tiktok")
    gemini_key = await get_effective_gemini_key(user, db)

    # 1. Cria a Tarefa-Pai no Kanban em estado de execução inicial do Agente 1
    task = Task(
        business_id=business.id,
        user_id=user.id,
        title=f"[Vídeo] {req.title}",
        description=f"Produção Multi-Agente (5 etapas) para pauta: {req.topic}",
        assignee="agent",
        status="awaiting_supervision",
        priority="high",
        source="agent",
        agent_action="orchestrate_video_pipeline",
        payload={
            "topic": req.topic,
            "format_type": req.format_type,
            "platform": req.target_platform,
            "tone": req.tone,
            "visual_style": req.visual_style,
            "voice_persona": req.voice_persona,
            "pause_after_script": True,
            "script_approved": False,
        },
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await db.flush()

    # 2. Executa exclusivamente o Agente 1 (ScriptAgent)
    ctx = AgentContext(
        task_id=task.id,
        business_id=business.id,
        user_id=user.id,
        title=req.title,
        topic=req.topic,
        context_text=req.topic,
        business_name=business.name,
        business_niche=business.niche or "",
        business_archetype=business.archetype or "",
        brand_rules=dict(business.brand_rules or {}) if business.brand_rules else {},
        format_type="short" if is_short else "long",
        target_platform=req.target_platform,
        tone=req.tone or "Envolvente, claro e cinematográfico",
        visual_style=req.visual_style or "",
        voice_persona=req.voice_persona or "pt-BR-AntonioNeural",
        gemini_key=gemini_key or "",
        pause_after_script=True,
    )
    script_agent = ScriptAgent()
    manifest = load_manifest(ctx)
    manifest = await script_agent.run(ctx=ctx, manifest=manifest, force_regenerate=True)
    save_manifest(ctx, manifest)

    assert manifest.script is not None
    script_art = manifest.script
    story_bible = script_art.visual_bible.model_dump()
    scenes_raw = [
        {
            "scene_number": sc.scene_number,
            "timestamp": f"00:{(sc.scene_number - 1) * 3:02d} - 00:{sc.scene_number * 3:02d}",
            "act": sc.act,
            "narration": sc.narration,
            "visual_prompt": sc.visual_prompt_en,
            "b_roll_description": f"{sc.camera_angle} ({sc.camera_motion})",
            "include_character": sc.include_character,
            "camera_angle": sc.camera_angle,
            "camera_motion": sc.camera_motion,
            "estimated_seconds": sc.estimated_seconds,
            "on_screen_text": sc.on_screen_text,
        }
        for sc in script_art.scenes
    ]
    full_text = script_art.full_narration

    # 3. Salva o roteiro como ContentAsset
    asset_type = "dark_script_short" if is_short else "dark_script_long"
    tracking_code = f"DARK-{secrets.token_hex(4).upper()}"
    asset = ContentAsset(
        business_id=business.id,
        tracking_code=tracking_code,
        type=asset_type,
        platform=req.target_platform,
        title=script_art.title,
        body=full_text,
        content={
            "hook": script_art.hook,
            "cta": script_art.cta,
            "scenes": scenes_raw,
            "visual_bible": story_bible,
            "seo_tags": script_art.seo_tags,
            "suggested_music": "",
            "voice_persona": req.voice_persona or script_art.voice_persona,
            "format_type": req.format_type,
            "visual_style": req.visual_style,
            "task_id": task.id,
        },
        version=1,
        funnel_stage="tof_attraction",
        status="supervision",
        created_at=now,
        updated_at=now,
    )
    db.add(asset)
    await db.flush()

    # 4. Cria item na Fila de Aprovação (Human-in-the-Loop antes dos Agentes 2-5)
    approval = ApprovalQueue(
        business_id=business.id,
        user_id=user.id,
        task_id=task.id,
        type="dark_script_approval",
        title=f"Revisar Roteiro (Agente 1): {asset.title}",
        summary=f"Roteiro ({len(scenes_raw)} cenas, {script_art.word_count} palavras, ~{script_art.estimated_total_seconds}s). Aprove para liberar Vídeo, Narração, Legendas e Montagem.",
        payload={
            "content_asset_id": asset.id,
            "task_id": task.id,
            "pipeline_pause_stage": "script",
            "tracking_code": tracking_code,
            "format_type": req.format_type,
            "platform": req.target_platform,
            "hook": script_art.hook,
            "scenes_count": len(scenes_raw),
            "scenes": scenes_raw,
            "visual_bible": story_bible,
            "voice_persona": req.voice_persona,
            "seo_tags": script_art.seo_tags,
        },
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(approval)
    await db.flush()
    asset.approval_queue_id = approval.id

    # 5. Cria as 5 subtarefas agrupadas no Kanban e atualiza status da Etapa 1
    orchestrator = VideoOrchestrator()
    subtasks = await orchestrator.ensure_stage_subtasks(db, task)
    await orchestrator._sync_stage_status_to_db(
        db=db,
        parent_task=task,
        subtasks=subtasks,
        stage=AgentStage.SCRIPT.value,
        status_val="awaiting_supervision",
        percent=100.0,
        message="Roteiro completo aguardando aprovação para gerar cenas, narração, legendas e vídeo.",
        manifest=manifest,
    )

    t_payload = dict(task.payload or {})
    t_payload.update({
        "content_asset_id": asset.id,
        "approval_id": approval.id,
        "scenes_count": len(scenes_raw),
        "visual_bible": story_bible,
    })
    task.payload = t_payload
    task.result = _manifest_to_task_result(
        manifest,
        summary_override=f"Agente 1 (Roteiro) concluído ({len(scenes_raw)} cenas, ~{script_art.estimated_total_seconds}s). Aguardando aprovação.",
    )
    task.status = "awaiting_supervision"
    task.status_log = "Aguardando aprovação do Roteiro (Agente 1) para iniciar Agentes 2 a 5 (20%)"

    await db.commit()
    await db.refresh(asset)

    formatted_scenes = [
        DarkScriptScene(
            scene_number=s.get("scene_number", idx + 1),
            timestamp=s.get("timestamp", f"00:{idx*3:02d} - 00:{(idx+1)*3:02d}"),
            narration=s.get("narration", ""),
            visual_prompt=s.get("visual_prompt", ""),
            b_roll_description=s.get("b_roll_description", ""),
            on_screen_text=s.get("on_screen_text"),
        )
        for idx, s in enumerate(scenes_raw)
    ]

    return {
        "id": asset.id,
        "business_id": business.id,
        "task_id": task.id,
        "title": asset.title,
        "format_type": req.format_type,
        "target_platform": req.target_platform,
        "hook": script_art.hook,
        "cta": script_art.cta,
        "full_narration": full_text,
        "visual_bible": story_bible,
        "scenes_count": len(formatted_scenes),
        "scenes": [s.model_dump() for s in formatted_scenes],
        "seo_tags": script_art.seo_tags,
        "suggested_music": None,
        "voice_persona": req.voice_persona,
        "approval_queue_id": approval.id,
        "status": asset.status,
        "created_at": asset.created_at,
    }


async def list_dark_scripts(db: AsyncSession, business_id: int) -> list[dict[str, Any]]:
    """Lista todos os roteiros e ativos de mídia de canal dark criados para o negócio."""
    res = await db.execute(
        select(ContentAsset)
        .where(
            ContentAsset.business_id == business_id,
            ContentAsset.type.in_(["dark_script_short", "dark_script_long", "video_script"]),
        )
        .order_by(ContentAsset.id.desc())
    )
    assets = res.scalars().all()
    results = []
    for a in assets:
        content_dict = a.content or {}
        scenes_data = content_dict.get("scenes", [])
        results.append({
            "id": a.id,
            "business_id": a.business_id,
            "parent_id": a.parent_id,
            "task_id": content_dict.get("task_id"),
            "video_url": content_dict.get("video_url"),
            "audio_url": content_dict.get("audio_url"),
            "srt_url": content_dict.get("srt_url"),
            "visual_bible": content_dict.get("visual_bible"),
            "title": a.title or "Sem título",
            "format_type": content_dict.get("format_type", "short" if a.type == "dark_script_short" else "long"),
            "target_platform": a.platform,
            "hook": content_dict.get("hook", ""),
            "cta": content_dict.get("cta", ""),
            "full_narration": a.body or "",
            "scenes_count": len(scenes_data),
            "scenes": scenes_data,
            "seo_tags": content_dict.get("seo_tags", []),
            "suggested_music": content_dict.get("suggested_music"),
            "voice_persona": content_dict.get("voice_persona"),
            "approval_queue_id": a.approval_queue_id,
            "status": a.status,
            "total_views": a.total_views,
            "total_clicks": a.total_clicks,
            "total_revenue_brl": float(a.total_revenue_brl),
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return results


async def mine_dark_channel_topics(business: Business) -> list[dict[str, Any]]:
    """Gera pautas e temas de alto potencial de cliques e retenção para o nicho do canal."""
    niche = (business.niche or "Mistérios & Curiosidades").lower()
    
    if "história" in niche or "guerra" in niche or "historia" in niche:
        topics = [
            {
                "topic": "O Batalhão Fantasma da Segunda Guerra Mundial",
                "predicted_ctr": "11.4%",
                "format_recommended": "long",
                "estimated_views": "250K - 800K",
                "hook_angle": "Militares que enganaram o exército inimigo com tanques infláveis e sons gravados.",
            },
            {
                "topic": "O Último Soldado Samurai que Não Sabia que a Guerra Havia Terminado",
                "predicted_ctr": "13.2%",
                "format_recommended": "short",
                "estimated_views": "1.2M - 3.5M",
                "hook_angle": "Hiroo Onoda lutou na selva por 29 anos após 1945 achando que ordens de rendição eram fake.",
            },
            {
                "topic": "O Mistério Inexplicável do Voo 19 no Triângulo das Bermudas",
                "predicted_ctr": "9.8%",
                "format_recommended": "long",
                "estimated_views": "180K - 500K",
                "hook_angle": "Cinco bombardeiros da Marinha desapareceram simultaneamente sem deixar vestígios.",
            },
        ]
    elif "finanças" in niche or "dinheiro" in niche or "negócio" in niche:
        topics = [
            {
                "topic": "Como a Família Rothschild Criou o Sistema Bancário Moderno",
                "predicted_ctr": "10.5%",
                "format_recommended": "long",
                "estimated_views": "300K - 900K",
                "hook_angle": "O mensageiro secreto que soube do resultado da Batalha de Waterloo antes de todo o parlamento.",
            },
            {
                "topic": "O Golpe Psicológico dos Supermercados que Faz Você Gastar 40% a Mais",
                "predicted_ctr": "14.1%",
                "format_recommended": "short",
                "estimated_views": "1.8M - 4.2M",
                "hook_angle": "Por que o pão fresco e as flores ficam sempre na entrada da loja?",
            },
            {
                "topic": "A Moeda que Derreteu um Império em 6 Meses",
                "predicted_ctr": "9.2%",
                "format_recommended": "long",
                "estimated_views": "150K - 450K",
                "hook_angle": "A hiperinflação de Weimar e a lição esquecida sobre ouro e dívida.",
            },
        ]
    else:
        topics = [
            {
                "topic": f"Os 3 Maiores Segredos Jamais Revelados sobre {business.niche or 'o Mundo Antigo'}",
                "predicted_ctr": "12.8%",
                "format_recommended": "short",
                "estimated_views": "850K - 2.1M",
                "hook_angle": "Se você acha que conhece a história toda, este único detalhe vai te assustar.",
            },
            {
                "topic": "A Descoberta Arqueológica que Ninguém Consegue Explicar",
                "predicted_ctr": "11.0%",
                "format_recommended": "long",
                "estimated_views": "400K - 1.1M",
                "hook_angle": "Artefatos com precisão milimétrica encontrados em camadas geológicas de 50 mil anos.",
            },
            {
                "topic": "Por Que a Ciência Não Consegue Decifrar Esse Fenômeno?",
                "predicted_ctr": "13.5%",
                "format_recommended": "short",
                "estimated_views": "1.5M - 3.8M",
                "hook_angle": "Cientistas que tentaram explicar o evento perderam os dados misteriosamente.",
            },
        ]
    return topics

