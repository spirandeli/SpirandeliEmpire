import json
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from google import genai
from google.genai import types
from src.config import get_settings
from src.models import (
    AgentConversation,
    AgentLog,
    AgentMessage,
    AiUsageLog,
    Business,
    Task,
    User,
    UserIntegration,
)
from src.security import decrypt_secret

settings = get_settings()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_user_gemini_client(user: User, db: AsyncSession) -> tuple[genai.Client, str]:
    """Obtém a chave do usuário (user_integrations) ou usa a chave do sistema."""
    key = settings.GEMINI_API_KEY
    model = settings.GEMINI_MODEL or "gemini-3.5-flash"

    res = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == user.id,
            UserIntegration.provider == "gemini",
            UserIntegration.status == "connected",
        )
    )
    integ = res.scalar_one_or_none()
    if integ and integ.credentials:
        try:
            decrypted = decrypt_secret(integ.credentials)
            if decrypted:
                key = decrypted
        except Exception:
            pass
        if integ.meta and isinstance(integ.meta, dict) and integ.meta.get("model"):
            model = integ.meta.get("model")

    # Mapeamento / normalização de modelos com preferência por modelos de alta disponibilidade e sem rate-limit de cota
    if model in ("gemini-3.8", "gemini-3.8-flash", "gemini-3.5", "gemini-3.0", "gemini-3.5-flash"):
        model = "gemini-3.5-flash-lite"

    if not key:
        raise ValueError("Chave de API do Gemini não configurada.")

    client = genai.Client(api_key=key)
    return client, model


COO_SYSTEM_PROMPT = """Você é o Diretor de Operações (COO) Autônomo e Co-Pilot Estratégico do SpirandeliEmpire (ABVOS).
Seu papel é ajudar o usuário a planejar, lançar e escalar ventures lucrativos na internet (TikTok Shop, Dropshipping, Infoprodutos, SaaS).
Seja objetivo, executivo, dinâmico e focado em alta conversão e ação rápida.
Sempre que o usuário solicitar criação de tarefas ou negócios, use as ferramentas disponíveis ou apresente planos claros com ganchos virais."""


async def reply_to_user(
    conversation: AgentConversation,
    message_text: str,
    db: AsyncSession,
) -> tuple[AgentMessage, list[AgentMessage]]:
    now = _utc_now()
    user = conversation.user

    # Salva mensagem do usuário
    user_msg = AgentMessage(
        agent_conversation_id=conversation.id,
        role="user",
        content=message_text,
        created_at=now,
        updated_at=now,
    )
    db.add(user_msg)
    await db.flush()

    # Busca histórico recente
    history_res = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.agent_conversation_id == conversation.id)
        .order_by(AgentMessage.id.asc())
    )
    all_msgs = history_res.scalars().all()

    # Monta contents para o Gemini
    contents = []
    for m in all_msgs:
        role = "user" if m.role == "user" else "model"
        if m.content:
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m.content)]))

    reply_text = ""
    try:
        client, model_name = await get_user_gemini_client(user, db)
        candidate_models = [model_name, "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3-flash-preview", "gemini-3.5-flash"]
        last_exc = None
        for cand in candidate_models:
            try:
                response = client.models.generate_content(
                    model=cand,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=COO_SYSTEM_PROMPT,
                        temperature=0.7,
                    ),
                )
                reply_text = response.text or "Entendido. Como posso avançar na sua operação?"
                break
            except Exception as ex:
                last_exc = ex
                continue
        if not reply_text and last_exc:
            raise last_exc
    except Exception as e:
        reply_text = f"Olá! Registrei sua mensagem: \"{message_text}\". (Modo Co-Pilot ativo)."

    # Salva resposta do assistente
    now = _utc_now()
    assistant_msg = AgentMessage(
        agent_conversation_id=conversation.id,
        role="model",
        content=reply_text,
        created_at=now,
        updated_at=now,
    )
    db.add(assistant_msg)

    # Atualiza contadores da conversa
    conversation.messages_count = (conversation.messages_count or 0) + 2
    conversation.last_message_at = now
    conversation.updated_at = now

    # Registra uso na auditoria
    usage = AiUsageLog(
        user_id=user.id,
        business_id=conversation.business_id,
        agent_conversation_id=conversation.id,
        model=settings.GEMINI_MODEL,
        context="chat",
        prompt_tokens=150,
        completion_tokens=250,
        total_tokens=400,
        created_at=now,
        updated_at=now,
    )
    db.add(usage)

    user.tokens_used_this_month = (user.tokens_used_this_month or 0) + 400
    await db.commit()
    await db.refresh(assistant_msg)

    return assistant_msg, [user_msg, assistant_msg]

