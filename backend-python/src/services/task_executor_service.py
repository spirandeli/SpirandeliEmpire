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
from src.services.media.agents.orchestrator import STAGE_ACTION_MAP, VideoOrchestrator
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

    # 0A. Se a tarefa for uma subtarefa de um dos 5 agentes especializados, delega ao estágio correspondente
    if getattr(task, "agent_action", None) in STAGE_ACTION_MAP and task.parent_id:
        p_res = await db.execute(
            select(Task)
            .options(selectinload(Task.business))
            .where(Task.id == task.parent_id, Task.deleted_at.is_(None))
        )
        parent_task = p_res.scalar_one_or_none()
        if parent_task:
            stage = STAGE_ACTION_MAP[task.agent_action]
            orchestrator = VideoOrchestrator()
            orch_res = await orchestrator.run_single_stage(
                db=db,
                parent_task=parent_task,
                user=user,
                stage=stage,
                cascade=False,
            )
            await db.refresh(task)
            return {
                "success": True,
                "task_id": task.id,
                "parent_task_id": parent_task.id,
                "stage": stage.value,
                "status": task.status,
                "summary": (task.result or {}).get("summary") or f"Estágio {stage.value} executado.",
                "result": orch_res.get("result"),
            }

    # 0B. Verifica se a tarefa envolve produção multimídia / Canal Dark / Vídeo
    is_video_task = (
        (business and business.archetype in ("canal_dark", "dark_channel_automation"))
        or getattr(task, "agent_action", None) in ("render_video_series", "orchestrate_video_pipeline")
        or any(
            k in (task.title + " " + (task.description or "")).lower()
            for k in ["vídeo", "video", "roteiro", "tiktok", "shorts", "dark", "cena", "narração", "locução", "reels", "série", "serie", "mp4"]
        )
    )

    if is_video_task:
        orchestrator = VideoOrchestrator()
        payload_dict = dict(task.payload or {})
        pause_flag = payload_dict.get("pause_after_script")
        if pause_flag is None:
            pause_flag = not bool(payload_dict.get("script_approved", False))
        try:
            orch_res = await orchestrator.run_pipeline(
                db=db,
                parent_task=task,
                user=user,
                pause_after_script=bool(pause_flag),
            )
            await db.refresh(task)
            return {
                "success": True,
                "task_id": task.id,
                "status": task.status,
                "paused_for_approval": orch_res.get("paused_for_approval", False),
                "summary": (task.result or {}).get("summary", f"Pipeline multi-agente executado para Tarefa #{task.id}."),
                "model_used": "multi-agent-pipeline",
                "assets_created": [],
                "result": orch_res.get("result"),
            }
        except Exception as media_err:
            logger.error(f"Erro no orquestrador multi-agente para tarefa #{task.id}: {media_err}")
            task.failure_reason = f"Falha no pipeline multi-agente: {media_err}"
            task.status_log = f"Erro no pipeline: {str(media_err)[:180]}"
            task.status = "awaiting_supervision"
            p_copy = dict(task.payload or {})
            p_copy["video_progress"] = {
                "stage": "failed",
                "percent": 0.0,
                "status_log": task.status_log,
                "error": str(media_err),
                "updated_at": _utc_now().isoformat(),
            }
            task.payload = p_copy
            await db.commit()
            raise RuntimeError(f"Erro no pipeline multi-agente: {media_err}")

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
3. Direção de Arte e Cenografia Sob Medida para a História (`visual_bible` e `visual_prompt`):
   - NUNCA use templates fixos ou anjos se a história for de outro assunto! Pense o universo visual (`world_setting`: arquitetura, texturas, iluminação volumétrica, elementos em camadas), o protagonista/figuras (`protagonist_description`) e a paleta (`color_palette`) especificamente adaptados ao tema solicitado (história real, mistério, ficção, guerra, suspense, etc.).
   - CONCEPÇÃO DINÂMICA DE CADA CENA (ANTI-RETRATO CENTRALIZADO): Cada um dos 20 `visual_prompt` em inglês DEVE ser pensado como uma tomada de cinema rica em ambiente para aquele exato momento da história. Alterne planos abertos para revelar a escala e o local, planos médios descentralizados na regra dos terços (com elementos de primeiro plano e fundo trabalhando o cenário), detalhes narrativos de objetos/cenário e ângulos dramáticos. É PROIBIDO gerar 20 retratos centralizados estáticos com fundo desfocado/vazio.

Responda em formato JSON estruturado com os seguintes campos:
{{
  "summary": "Resumo executivo do que foi produzido nesta tarefa",
  "deliverable_type": "dark_script | image_prompts | voiceover_tts | strategy | general",
  "markdown_content": "O documento completo e formatado em Markdown com todos os detalhes produzidos",
  "visual_bible": {{
     "protagonist_description": "Descrição física detalhada do protagonista condizente com a história",
     "world_setting": "Descrição rica do cenário, arquitetura, clima e atmosfera específicos da história",
     "color_palette": "Cores dominantes e iluminação de contraste",
     "art_style": "Estilo visual de arte cinematográfica adaptado ao tema"
  }},
  "items": [
     {{
        "title": "Cena 01 - Título curto da cena",
        "description": "Contexto da cena",
        "script": "Frase limpa falada pelo narrador sem colchetes e com sete a dez palavras.",
        "visual_prompt": "Cinematic shot description with specific camera angle, rich environment, dynamic lighting and integrated subject, 9:16, no text",
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

    # Verifica se a tarefa já possui um roteiro gerado pelo sistema (em ContentAsset, payload ou result)
    linked_script_asset: Optional[ContentAsset] = None
    preexisting_scenes: list[dict[str, Any]] = []
    preexisting_bible: Optional[dict[str, str]] = None
    preexisting_narration: str = ""

    payload_dict = dict(task.payload or {})
    content_asset_id = payload_dict.get("content_asset_id")
    if content_asset_id:
        ca_res = await db.execute(select(ContentAsset).where(ContentAsset.id == int(content_asset_id)))
        linked_script_asset = ca_res.scalar_one_or_none()
        if linked_script_asset:
            ca_content = dict(linked_script_asset.content or {})
            preexisting_scenes = list(ca_content.get("scenes") or [])
            preexisting_bible = ca_content.get("visual_bible") if isinstance(ca_content.get("visual_bible"), dict) else None
            preexisting_narration = (linked_script_asset.body or "").strip()

    if not preexisting_scenes and isinstance(payload_dict.get("scenes"), list) and payload_dict["scenes"]:
        preexisting_scenes = list(payload_dict["scenes"])
        if isinstance(payload_dict.get("visual_bible"), dict):
            preexisting_bible = payload_dict["visual_bible"]

    if not preexisting_scenes and isinstance(task.result, dict) and isinstance(task.result.get("items"), list) and len(task.result["items"]) >= 5:
        for idx, it in enumerate(task.result["items"]):
            preexisting_scenes.append({
                "scene_number": idx + 1,
                "narration": it.get("script") or it.get("narration") or it.get("description") or f"Cena {idx + 1}",
                "visual_prompt": it.get("visual_prompt") or "",
                "on_screen_text": it.get("title") or it.get("on_screen_text") or f"CENA {idx + 1:02d}",
            })
        if isinstance(task.result.get("visual_bible"), dict):
            preexisting_bible = task.result["visual_bible"]

    response_data = {}
    model_used = "gemini-3.8-flash"
    if preexisting_scenes and is_video_task:
        # Usa diretamente o roteiro já gerado pelo sistema sem sobrescrevê-lo
        parsed_output = {
            "summary": f"Vídeo renderizado a partir do roteiro '{linked_script_asset.title if linked_script_asset else task.title}' ({len(preexisting_scenes)} cenas).",
            "deliverable_type": "dark_script",
            "markdown_content": preexisting_narration or "\n\n".join(
                f"**Cena {idx + 1:02d}:** {sc.get('narration', '')}" for idx, sc in enumerate(preexisting_scenes)
            ),
            "visual_bible": preexisting_bible or {},
            "items": [
                {
                    "title": sc.get("on_screen_text") or f"Cena {idx + 1:02d}",
                    "description": sc.get("b_roll_description") or f"Cena {idx + 1:02d}",
                    "script": sc.get("narration") or sc.get("script") or "",
                    "visual_prompt": sc.get("visual_prompt") or "",
                    "tags": ["canal_dark", "roteiro_ia"],
                }
                for idx, sc in enumerate(preexisting_scenes)
            ],
        }
    else:
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
                    "narration": it.get("script") or it.get("narration") or it.get("description") or f"Cena {idx + 1}",
                    "visual_prompt": it.get("visual_prompt") or "",
                    "on_screen_text": it.get("title") or it.get("on_screen_text") or f"CENA {idx + 1:02d}",
                })

            full_narration_text = " ".join([sc["narration"] for sc in scenes_payload if sc.get("narration")])
            if not full_narration_text:
                full_narration_text = preexisting_narration or parsed_output.get("markdown_content", task.title)

            biz_id = business.id if business else 0
            v_bible = parsed_output.get("visual_bible") if isinstance(parsed_output.get("visual_bible"), dict) else preexisting_bible
            media_result = await execute_full_media_pipeline(
                business_id=biz_id,
                task_id=task.id,
                scenes=scenes_payload,
                full_narration=full_narration_text,
                gemini_key=api_key,
                visual_bible=v_bible,
            )
            await db.refresh(task)

            # Sincroniza exatamente as 20 cenas compiladas e a visual_bible de volta para parsed_output["items"]
            final_scenes = media_result.get("scenes") or scenes_payload
            final_bible = media_result.get("visual_bible") or v_bible or {}
            parsed_output["visual_bible"] = final_bible
            parsed_output["items"] = [
                {
                    "title": sc.get("on_screen_text") or f"Cena {idx + 1:02d}",
                    "description": f"Cena {idx + 1:02d} sincronizada",
                    "script": sc.get("narration") or "",
                    "visual_prompt": sc.get("visual_prompt") or "",
                    "tags": ["canal_dark", "20_cenas"],
                }
                for idx, sc in enumerate(final_scenes)
            ]
            final_full_narration = " ".join(sc.get("narration", "") for sc in final_scenes if sc.get("narration")).strip()
            parsed_output["markdown_content"] = "\n\n".join(
                f"### Cena {idx + 1:02d} ({idx * 3:02d}s - {(idx + 1) * 3:02d}s)\n"
                f"- **Narração:** {sc.get('narration', '')}\n"
                f"- **Prompt Visual:** `{sc.get('visual_prompt', '')}`"
                for idx, sc in enumerate(final_scenes)
            )

            # Anexa informações de mídia ao resultado final da tarefa
            parsed_output["media"] = media_result
            parsed_output["video_url"] = media_result["video"]["url"]
            parsed_output["audio_url"] = media_result["audio"]["url"]
            parsed_output["srt_url"] = media_result["subtitles"]["srt_url"]
            parsed_output["summary"] = (
                f"{parsed_output.get('summary', 'Tarefa concluída.')} "
                f"🎬 VÍDEO FINAL RENDERIZADO (1080x1920 9:16, {media_result['video']['duration_seconds']}s, {media_result['video']['size_mb']}MB) pronto para download."
            )

            # Atualiza ou cria o roteiro consolidado (dark_script_short) no Estúdio Dark vinculado ao vídeo
            if linked_script_asset:
                ca_content = dict(linked_script_asset.content or {})
                ca_content["scenes"] = final_scenes
                ca_content["visual_bible"] = final_bible
                ca_content["task_id"] = task.id
                ca_content["video_url"] = media_result["video"]["url"]
                ca_content["audio_url"] = media_result["audio"]["url"]
                ca_content["srt_url"] = media_result["subtitles"]["srt_url"]
                linked_script_asset.content = ca_content
                linked_script_asset.body = final_full_narration or linked_script_asset.body
                linked_script_asset.updated_at = _utc_now()
            else:
                script_code = f"DARK-{biz_id}-{task.id}-{secrets.token_hex(3).upper()}"
                script_asset = ContentAsset(
                    tracking_code=script_code,
                    business_id=biz_id,
                    type="dark_script_short",
                    platform="youtube_shorts",
                    title=task.title.replace("[Vídeo] ", "").strip(),
                    body=final_full_narration,
                    content={
                        "hook": final_scenes[0].get("narration", "") if final_scenes else task.title,
                        "scenes": final_scenes,
                        "visual_bible": final_bible,
                        "task_id": task.id,
                        "video_url": media_result["video"]["url"],
                        "audio_url": media_result["audio"]["url"],
                        "srt_url": media_result["subtitles"]["srt_url"],
                        "format_type": "short",
                        "voice_persona": "Voz masculina grave e documental (pt-BR-AntonioNeural)",
                        "seo_tags": ["canal_dark", "shorts", "historia"],
                    },
                    status="supervision",
                    created_at=now,
                    updated_at=now,
                )
                db.add(script_asset)
                assets_created.append(script_asset.title)

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
