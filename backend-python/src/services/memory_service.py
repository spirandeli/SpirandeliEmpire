from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import AgentMemory, AgentMessage


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_contextual_memories(
    db: AsyncSession,
    user_id: int,
    business_id: Optional[int] = None,
    limit: int = 8,
) -> list[AgentMemory]:
    """Recupera memórias de longo prazo (diretrizes estratégicas, preferências, fatos consolidados)."""
    query = select(AgentMemory).where(AgentMemory.user_id == user_id)
    if business_id:
        query = query.where(
            (AgentMemory.business_id == business_id) | (AgentMemory.business_id.is_(None))
        )
    query = query.order_by(AgentMemory.importance.desc(), AgentMemory.id.desc()).limit(limit)
    res = await db.execute(query)
    return list(res.scalars().all())


async def save_agent_memory(
    db: AsyncSession,
    user_id: int,
    key: str,
    content: str,
    category: str = "fact",
    importance: int = 5,
    business_id: Optional[int] = None,
) -> AgentMemory:
    """Registra ou atualiza uma memória de longo prazo."""
    now = _utc_now()
    # Verifica se já existe uma memória com essa chave para o usuário
    res = await db.execute(
        select(AgentMemory).where(
            AgentMemory.user_id == user_id,
            AgentMemory.key == key,
            AgentMemory.business_id == business_id,
        )
    )
    existing = res.scalar_one_or_none()
    if existing:
        existing.content = content
        existing.category = category
        existing.importance = max(existing.importance, importance)
        existing.updated_at = now
        await db.commit()
        await db.refresh(existing)
        return existing

    mem = AgentMemory(
        user_id=user_id,
        business_id=business_id,
        category=category,
        key=key,
        content=content,
        importance=importance,
        created_at=now,
        updated_at=now,
    )
    db.add(mem)
    await db.commit()
    await db.refresh(mem)
    return mem


def format_memories_prompt(memories: list[AgentMemory]) -> str:
    """Formata as memórias recuperadas para injeção no prompt de sistema."""
    if not memories:
        return ""

    lines = ["\n[MEMÓRIAS DE LONGO PRAZO & DIRETRIZES ESTRATÉGICAS DO OPERADOR]:"]
    for m in memories:
        cat = m.category.upper()
        lines.append(f"- [{cat} | {m.key}] (Importância {m.importance}/10): {m.content}")

    return "\n".join(lines) + "\n"

