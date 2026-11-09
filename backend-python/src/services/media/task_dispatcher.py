"""
Dispatcher de Tarefas de Vídeo em Lote para Séries (ABVOS).
Cria automaticamente as tarefas no Kanban para cada parte da série,
gerenciando ciclo de vida, status e integração com o worker de renderização.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.models import Task, Business, User

logger = logging.getLogger("abvos.media.dispatcher")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def dispatch_series_video_tasks(
    db: AsyncSession,
    user_id: int,
    business_id: int,
    series_title: str = "Série 01 - A Queda de Lúcifer",
    parts_count: int = 3,
    auto_execute_part_1: bool = False,
    custom_scripts: Optional[List[Dict[str, Any]]] = None,
) -> List[Task]:
    """
    Registra em lote no banco de dados as tarefas do Kanban para uma série:
    1. [Vídeo] Série 01 - Parte 1 (Geração de Assets, TTS e FFmpeg)
    2. [Vídeo] Série 01 - Parte 2 (Geração de Assets, TTS e FFmpeg)
    3. [Vídeo] Série 01 - Parte 3 (Geração de Assets, TTS e FFmpeg)
    """
    now = _utc_now()
    created_tasks: List[Task] = []

    # Extrai o prefixo da série caso venha customizado
    series_clean = series_title.strip()
    if not series_clean:
        series_clean = "Série 01 - A Queda de Lúcifer"

    # Conteúdo roteirizado padrão de alta retenção para "A Queda de Lúcifer" ou genérico
    default_scripts = [
        {
            "part": 1,
            "theme": "A Luz Antes da Queda",
            "hook": "Antes de ser lançado às trevas eternas, ele era o ser mais belo e perfeito de toda a criação...",
            "description": "Geração de Assets, TTS e FFmpeg para a Parte 1: O ápice celestial e o nascimento do orgulho cósmico.",
        },
        {
            "part": 2,
            "theme": "A Rebelião nos Céus",
            "hook": "Um terço das estrelas do céu foi arrastado quando a primeira grande batalha cósmica começou...",
            "description": "Geração de Assets, TTS e FFmpeg para a Parte 2: O confronto entre Miguel e Lúcifer nas esferas superiores.",
        },
        {
            "part": 3,
            "theme": "O Abismo e o Legado",
            "hook": "E ele caiu como um raio do céu... direto para o abismo de fogo e cinzas que moldaria a história humana.",
            "description": "Geração de Assets, TTS e FFmpeg para a Parte 3: A queda na terra primordial e o início da guerra invisível.",
        },
    ]

    for part_idx in range(1, parts_count + 1):
        task_title = f"[Vídeo] {series_clean} - Parte {part_idx} (Geração de Assets, TTS e FFmpeg)"

        # Verifica se já existe tarefa com o mesmo título para evitar duplicação no seed
        stmt = select(Task).where(
            Task.business_id == business_id,
            Task.user_id == user_id,
            Task.title == task_title,
            Task.deleted_at.is_(None),
        )
        existing_res = await db.execute(stmt)
        existing = existing_res.scalar_one_or_none()
        if existing:
            logger.info(f"Tarefa já existente no Kanban: {task_title} (ID #{existing.id})")
            created_tasks.append(existing)
            continue

        script_meta = default_scripts[(part_idx - 1) % len(default_scripts)]
        initial_status = "in_progress_agent" if (part_idx == 1 and auto_execute_part_1) else "backlog"
        initial_progress_text = "Iniciando geração de prompts... (0%)" if initial_status == "in_progress_agent" else "Aguardando início no Kanban..."

        task = Task(
            business_id=business_id,
            user_id=user_id,
            title=task_title,
            description=f"{initial_progress_text}\n\n{script_meta['description']}",
            assignee="agent",
            status=initial_status,
            priority="high",
            source="agent",
            position=part_idx,
            agent_action="render_video_series",
            payload={
                "series_title": series_clean,
                "part": part_idx,
                "total_parts": parts_count,
                "scenes_count": 20,
                "theme": script_meta["theme"],
                "hook": script_meta["hook"],
                "video_progress": {
                    "stage": "prompts" if initial_status == "in_progress_agent" else "pending",
                    "percent": 0.0,
                    "status_text": initial_progress_text,
                    "current_scene": 0,
                    "total_scenes": 20,
                    "output_path": "/app/storage/output/",
                    "updated_at": now.isoformat(),
                },
            },
            status_log=initial_progress_text,
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        created_tasks.append(task)

    await db.commit()
    for t in created_tasks:
        await db.refresh(t)

    logger.info(f"Disparadas {len(created_tasks)} tarefas de vídeo para a série '{series_clean}' (Business #{business_id})")
    return created_tasks

