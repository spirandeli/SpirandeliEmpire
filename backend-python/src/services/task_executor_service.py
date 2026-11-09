import json
import logging
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.models import (
    AgentLog,
    ApprovalQueue,
    Business,
    ContentAsset,
    Task,
    User,
)
from src.services.jeffrey_orchestrator import call_gemini_generate_content, get_effective_gemini_key
from src.services.media.pipeline import execute_full_media_pipeline, _persist_video_progress

logger = logging.getLogger("abvos.task_executor")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def execute_agent_task(
    db: AsyncSession,
    task_id: int,
    user: User,
) -> dict[str, Any]:
    """
    Executa uma tarefa atribuída à IA Worker utilizando Gemini 3.8.
    Gera os entregáveis completos, salva em task.result, cria os ContentAssets
    pertinentes (ex: roteiros dark no Estúdio) e encaminha para a Fila de Supervisão.
    """
    res = await db.execute(
        select(Task)
        .options(selectinload(Task.business))
        .where(
            Task.id == task_id,
            Task.user_id == user.id,
            Task.deleted_at.is_(None),
        )
    )
    task = res.scalar_one_or_none()
    if not task:
        raise ValueError(f"Tarefa #{task_id} não encontrada.")

    business: Optional[Business] = task.business
    now = _utc_now()
    task.started_at = now

    api_key = await get_effective_gemini_key(user, db)

    biz_info = ""
    if business:
        biz_info = f"""
NEGÓCIO RELACIONADO:
- Nome: {business.name}
- Nicho: {business.niche}
- Arquétipo: {business.archetype} ({business.type})
- Regras de Marca / Tom: {json.dumps(business.brand_rules, ensure_ascii=False) if business.brand_rules else 'Padrão'}
"""

    system_prompt = f"""Você é o Especialista em Execução Autônoma de Tarefas de IA do SpirandeliEmpire (ABVOS).
Sua missão é EXECUTAR integralmente a tarefa solicitada com excelência e profundidade, gerando os entregáveis práticos e finais sem respostas vagas ou incompletas.
{biz_info}

Diretrizes Obrigatórias para Canal Dark (Roteiros, Narrações e Imagens de Vídeo 60s):
1. Roteiro Sequencial de 20 Cenas: Sempre que a tarefa envolver vídeo, roteiro, série ou Canal Dark, gere EXATAMENTE 20 itens dentro da lista `items` (Cena 01 até Cena 20), formando UMA ÚNICA HISTÓRIA CONTÍNUA, cronológica e hipnótica de 60 segundos (3 segundos por cena).
2. Narração Limpa (`script`): Em cada uma das 20 cenas, o campo `script` deve conter APENAS a frase falada em português natural (entre 7 e 10 palavras por cena, conectando-se com a cena seguinte). É ESTRITAMENTE PROIBIDO incluir `[pausa]`, colchetes, `(fase 2)`, parênteses de direção de palco ou prefixos como `Cena 1:` dentro de `script`.
3. Bíblia Visual da História (`visual_bible`) e Continuidade Entre Cenas (`visual_prompt`):
   - Defina o objeto `visual_bible` com a aparência física IMUTÁVEL do protagonista (`protagonist_description`: gênero, feições do rosto, cor/corte de cabelo, cor dos olhos, armadura/traje), cenário contínuo (`world_setting`), paleta de cores (`color_palette`) e estilo (`art_style`).
   - Em cada uma das 20 cenas, o `visual_prompt` em inglês DEVE repetir as características físicas do protagonista de `visual_bible` e descrever uma cena física concreta no mesmo universo (nunca mude de personagem, estilo ou escreva metáforas abstratas).

Responda em formato JSON estruturado com os seguintes campos:
{{
  "summary": "Resumo executivo do que foi produzido nesta tarefa",
  "deliverable_type": "dark_script | image_prompts | voiceover_tts | strategy | general",
  "markdown_content": "O documento completo e formatado em Markdown com todos os detalhes produzidos",
  "visual_bible": {{
     "protagonist_description": "tall male celestial archangel with long flowing platinum-silver hair, sharp glowing golden amber eyes, sculpted face, ornate black-and-gold celestial armor and six dark-golden feathered wings",
     "world_setting": "ancient monumental gothic celestial sanctuary of dark obsidian and golden marble pillars",
     "color_palette": "deep obsidian black, radiant molten gold, and cold astral sapphire blue",
     "art_style": "dark epic anime cinematic painting in the style of Castlevania and Fate/Zero, consistent character sheet"
  }},
  "items": [
     {{
        "title": "Cena 01 - Título curto da cena",
        "description": "Contexto da cena",
        "script": "Frase limpa falada pelo narrador sem colchetes e com sete a dez palavras.",
        "visual_prompt": "Same tall male celestial archangel with long platinum-silver hair, golden eyes and black-and-gold armor in the gothic celestial sanctuary, dramatic volumetric lighting, 9:16, no text",
        "tags": ["tag1", "tag2"]
     }}
  ]
}}
"""

    user_prompt = f"""TAREFA OPERACIONAL A SER EXECUTADA:
ID da Tarefa: #{task.id}
Título: {task.title}
Instruções / Escopo: {task.description or 'Execute a tarefa com profundidade total e gere todo o conteúdo prático.'}
Prioridade: {task.priority}

Produza agora o entregável final estruturado."""

    payload_contents = [
        {"role": "user", "parts": [{"text": user_prompt}]}
    ]

    # Verifica se a tarefa envolve produção multimídia / Canal Dark / Vídeo
    is_video_task = (
        (business and business.archetype in ("canal_dark", "dark_channel_automation"))
        or getattr(task, "agent_action", None) == "render_video_series"
        or any(
            k in (task.title + " " + (task.description or "")).lower()
            for k in ["vídeo", "video", "roteiro", "tiktok", "shorts", "dark", "cena", "narração", "locução", "reels", "série", "serie", "mp4"]
        )
    )

    if is_video_task:
        task.status = "in_progress_agent"
        task.failure_reason = None
        await db.commit()
        await _persist_video_progress(
            task_id=task.id,
            business_id=business.id if business else 0,
            current_scene=0,
            total_scenes=20,
            stage="prompts",
            percent=0.0,
        )

    response_data = {}
    model_used = "gemini-3.8-flash"
    try:
        response_data, model_used = await call_gemini_generate_content(
            api_key=api_key,
            contents=payload_contents,
            system_instruction=system_prompt,
            tools_declarations=[],
            preferred_model="gemini-3.8-flash",
        )
    except Exception as e:
        logger.warning(f"Aviso ao consultar Gemini para tarefa #{task.id}: {e}")
        if not is_video_task:
            task.failure_reason = str(e)
            task.attempts += 1
            await db.commit()
            raise RuntimeError(f"Erro na execução da IA: {e}")
        model_used = "abvos-autonomous-video-engine"

    raw_text = ""
    candidates = response_data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        if parts:
            raw_text = parts[0].get("text", "")

    parsed_output = {}
    clean_text = raw_text.strip()
    if "```json" in clean_text:
        clean_text = clean_text.split("```json")[1].split("```")[0].strip()
    elif "```" in clean_text:
        clean_text = clean_text.split("```")[1].split("```")[0].strip()

    try:
        parsed_output = json.loads(clean_text) if clean_text else {}
    except Exception:
        parsed_output = {}

    if not parsed_output:
        parsed_output = {
            "summary": f"Entrega da tarefa '{task.title}' concluída com sucesso pelo IA Worker.",
            "deliverable_type": "dark_script" if is_video_task else "general",
            "markdown_content": raw_text or task.description or task.title,
            "items": [],
        }

    media_result = None
    assets_created = []

    if is_video_task:
        try:
            logger.info(f"Disparando Pipeline Multimídia Autônomo para a Tarefa #{task.id}...")
            raw_items = parsed_output.get("items", [])
            scenes_payload = []

            for idx, it in enumerate(raw_items):
                scenes_payload.append({
                    "scene_number": idx + 1,
                    "narration": it.get("script") or it.get("description") or f"Cena {idx + 1}",
                    "visual_prompt": it.get("visual_prompt") or f"Cinematic dark scene, Unreal Engine 5, 8k, 9:16",
                    "on_screen_text": it.get("title") or f"CENA {idx + 1}",
                })

            full_narration_text = " ".join([sc["narration"] for sc in scenes_payload if sc.get("narration")])
            if not full_narration_text:
                full_narration_text = parsed_output.get("markdown_content", task.title)

            biz_id = business.id if business else 0
            v_bible = parsed_output.get("visual_bible") if isinstance(parsed_output.get("visual_bible"), dict) else None
            media_result = await execute_full_media_pipeline(
                business_id=biz_id,
                task_id=task.id,
                scenes=scenes_payload,
                full_narration=full_narration_text,
                gemini_key=api_key,
                visual_bible=v_bible,
            )
            await db.refresh(task)

            # Anexa informações de mídia ao resultado final da tarefa
            parsed_output["media"] = media_result
            parsed_output["video_url"] = media_result["video"]["url"]
            parsed_output["audio_url"] = media_result["audio"]["url"]
            parsed_output["srt_url"] = media_result["subtitles"]["srt_url"]
            parsed_output["summary"] = (
                f"{parsed_output.get('summary', 'Tarefa concluída.')} "
                f"🎬 VÍDEO FINAL RENDERIZADO (1080x1920 9:16, {media_result['video']['duration_seconds']}s, {media_result['video']['size_mb']}MB) pronto para download."
            )

            # Cria ContentAsset com o vídeo renderizado
            unique_code = f"VID-{biz_id}-{task.id}-{secrets.token_hex(3)}"
            asset = ContentAsset(
                tracking_code=unique_code,
                business_id=biz_id,
                type="rendered_dark_video",
                platform="youtube_shorts",
                title=f"[Vídeo 9:16] {task.title}",
                body=media_result["video"]["url"],
                content={
                    "video": media_result["video"],
                    "audio": media_result["audio"],
                    "subtitles": media_result["subtitles"],
                    "scenes_count": media_result["scenes_count"],
                    "format_type": "short_9x16",
                },
                status="pending_approval",
                created_at=now,
            )
            db.add(asset)
            assets_created.append(asset.title)

        except Exception as media_err:
            logger.error(f"Erro ao executar pipeline multimídia para tarefa #{task.id}: {media_err}")
            parsed_output["media_error"] = str(media_err)
            task.failure_reason = f"Falha no pipeline de vídeo (VPS): {str(media_err)}"
            task.status_log = f"Erro na renderização: {str(media_err)[:180]}"
            payload_copy = dict(task.payload or {})
            payload_copy["video_progress"] = {
                "stage": "failed",
                "percent": 0.0,
                "status_log": task.status_log,
                "error": str(media_err),
                "updated_at": _utc_now().isoformat(),
            }
            task.payload = payload_copy

    # Se for venture de Canal Dark, registra também os roteiros como ContentAsset se ainda não registrados
    if business and business.archetype in ("canal_dark", "dark_channel_automation") and not media_result:
        items = parsed_output.get("items", [])
        if items:
            for idx, it in enumerate(items[:10]):
                script_body = it.get("script") or it.get("description") or parsed_output.get("markdown_content", "")
                unique_code = f"DK-{business.id}-{task.id}-{secrets.token_hex(3)}"
                asset = ContentAsset(
                    tracking_code=unique_code,
                    business_id=business.id,
                    type="dark_script_short",
                    platform="youtube_shorts",
                    title=it.get("title", f"{task.title} - Item {idx+1}"),
                    body=script_body,
                    content={
                        "hook": it.get("title", "") or script_body[:80],
                        "scenes": [
                            {
                                "scene_number": 1,
                                "narration": script_body,
                                "visual_prompt": it.get("visual_prompt", "Cinematic dark anime, highly detailed, 8k, volumetric light, 9:16 aspect ratio"),
                            }
                        ],
                        "format_type": "short",
                        "voice_persona": "Voz grave, imponente e documental (ElevenLabs)",
                        "seo_tags": it.get("tags", ["canal_dark", "anime_biblico", "historia"]),
                    },
                    status="pending_approval",
                    created_at=now,
                )
                db.add(asset)
                assets_created.append(asset.title)
        else:
            # Cria 1 asset abrangente com o markdown gerado
            unique_code = f"DK-{business.id}-{task.id}-{secrets.token_hex(3)}"
            asset = ContentAsset(
                tracking_code=unique_code,
                business_id=business.id,
                type="video_script",
                platform="youtube_shorts",
                title=task.title,
                body=parsed_output.get("markdown_content", ""),
                content={
                    "hook": task.title,
                    "scenes": [],
                    "format_type": "short",
                    "voice_persona": "Voz grave, imponente e documental (ElevenLabs)",
                    "seo_tags": ["canal_dark", "anime_biblico"],
                },
                status="pending_approval",
                created_at=now,
            )
            db.add(asset)
            assets_created.append(asset.title)

    # Cria item na Fila de Supervisão Humana (ApprovalQueue)
    approval = ApprovalQueue(
        business_id=business.id if business else 0,
        user_id=user.id,
        task_id=task.id,
        type="task_deliverable",
        title=f"Revisão: {task.title}",
        summary=parsed_output.get("summary", f"Entregável gerado para a tarefa #{task.id}"),
        payload={
            "task_id": task.id,
            "task_title": task.title,
            "model_used": model_used,
            "result": parsed_output,
        },
        status="pending",
        priority=task.priority,
        agent_confidence=Decimal("0.96"),
        created_at=now,
        updated_at=now,
    )
    db.add(approval)

    # Atualiza tarefa
    task.result = parsed_output
    if media_result and media_result.get("success"):
        task.status = "done"
        task.failure_reason = None
        task.completed_at = now
    elif is_video_task and parsed_output.get("media_error"):
        task.status = "awaiting_supervision"
        task.completed_at = None
    else:
        task.status = "awaiting_supervision"
        task.completed_at = now
    task.updated_at = now

    # Registra Log Operacional
    log = AgentLog(
        user_id=user.id,
        business_id=business.id if business else None,
        task_id=task.id,
        level="info",
        event="task_executed_by_agent",
        message=f"IA Worker executou a tarefa #{task.id} '{task.title}' com sucesso ({model_used}).",
        context={"task_id": task.id, "model": model_used, "assets_count": len(assets_created)},
        created_at=now,
    )
    db.add(log)

    await db.commit()
    await db.refresh(task)

    return {
        "success": True,
        "task_id": task.id,
        "status": task.status,
        "status_label": "Aguardando Supervisão",
        "summary": parsed_output.get("summary"),
        "model_used": model_used,
        "assets_created": assets_created,
        "result": task.result,
    }
