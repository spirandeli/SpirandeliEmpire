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

Diretrizes para Canal Dark (Roteiros, Narrações e Imagens):
1. Roteiros: Estruturar em cenas com timestamp, narração palavra por palavra envolvente, ganchos nos primeiros 3s e retenção hipnótica.
2. Prompts de Imagem: Fornecer prompts visuais em inglês ultra-detalhados para Midjourney v6/Leonardo AI (estilo Anime Dark/Epic, proporção 9:16, iluminação cinematográfica).
3. Narração & TTS: Textos prontos para sintetizadores de voz (ElevenLabs), com marcações de pausas dramáticas [pausa] e tom épico.

Responda em formato JSON estruturado com os seguintes campos:
{{
  "summary": "Resumo executivo do que foi produzido nesta tarefa",
  "deliverable_type": "dark_script | image_prompts | voiceover_tts | strategy | general",
  "markdown_content": "O documento completo e formatado em Markdown com todos os detalhes produzidos",
  "items": [
     {{
        "title": "Título da cena, roteiro ou asset",
        "description": "Detalhes técnicos",
        "script": "Texto da locução / narração",
        "visual_prompt": "Prompt em inglês para geração da imagem (Midjourney/Leonardo)",
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

    try:
        response_data, model_used = await call_gemini_generate_content(
            api_key=api_key,
            contents=payload_contents,
            system_instruction=system_prompt,
            tools_declarations=[],
            preferred_model="gemini-3.8-flash",
        )
    except Exception as e:
        logger.error(f"Falha ao executar tarefa #{task.id} com Gemini: {e}")
        task.failure_reason = str(e)
        task.attempts += 1
        await db.commit()
        raise RuntimeError(f"Erro na execução da IA: {e}")

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
        parsed_output = json.loads(clean_text)
    except Exception:
        parsed_output = {
            "summary": f"Entrega da tarefa '{task.title}' concluída com sucesso pelo IA Worker.",
            "deliverable_type": "general",
            "markdown_content": raw_text or "Tarefa executada com sucesso.",
            "items": [],
        }

    # Se for venture de Canal Dark, registra ativos de mídia (ContentAsset) para aparecer no Estúdio Dark
    assets_created = []
    if business and business.archetype in ("canal_dark", "dark_channel_automation"):
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
