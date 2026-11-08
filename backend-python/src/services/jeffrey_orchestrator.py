import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.config import get_settings
from src.models import (
    AgentConversation,
    AgentLog,
    AgentMessage,
    AiUsageLog,
    Business,
    User,
    UserIntegration,
)
from src.security import decrypt_secret
from src.services.agent_tools import (
    execute_agent_tool,
    get_gemini_tools_declarations,
    TOOL_METADATA,
)
from src.services.memory_service import (
    get_contextual_memories,
    format_memories_prompt,
    save_agent_memory,
)

logger = logging.getLogger("abvos.jeffrey_orchestrator")
settings = get_settings()

MAX_REACT_STEPS = 5
FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_effective_gemini_key(user: User, db: AsyncSession) -> str:
    """Recupera a chave do usuário ou a chave de sistema."""
    key = settings.GEMINI_API_KEY
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
    return key or ""


def build_system_instruction(
    user: User,
    business: Optional[Business],
    memories_str: str,
) -> str:
    biz_context = ""
    if business:
        biz_context = f"""
[CONTEXTO DO NEGÓCIO ATIVO]:
- ID: {business.id} | Nome: {business.name} | Slug: {business.slug}
- Arquétipo: {business.archetype} | Nicho: {business.niche or 'Não especificado'}
- Métrica Norte: {business.north_star_metric} | Meta KPI: R$ {float(business.target_kpi_value or 0):.2f}
- Status: {business.status}
"""

    return f"""Você é Jeffrey, Diretor de Operações (COO) Executivo do SpirandeliEmpire (ABVOS).
Seu objetivo é ajudar o operador ({user.name}) a conceber, operar e escalar ventures digitais de alta margem (TikTok Shop Affiliate, Canais Dark no YouTube/TikTok, Dropshipping de Alto Ticket, SaaS Bootstrapped) com máxima autonomia e segurança.

POSTURA & DIRETRIZES:
1. Seja analítico, estratégico, decisivo, orientado a ROI e dinâmico.
2. Não fique apenas sugerindo ideias em texto abstrato: sempre que oportuno, USE AS FERRAMENTAS DISPONÍVEIS para consultar o sistema ou agir diretamente (ex: consultar métricas da VPS, checar Docker, criar novas ventures, despachar tarefas no Kanban ou submeter entregáveis à Supervisão Humana).
3. Playbook de Canais Dark (YouTube & TikTok):
   - Foco obsessivo em Retenção (AVD) nos primeiros 3-5 segundos e quebra de padrão.
   - Em roteiros longos (8-12 min), estruture em 5 atos com mini-cliffhangers a cada 90s.
   - Para cada cena, sugira prompts visuais ricos para Midjourney/Leonardo/Runway e instruções de voz para ElevenLabs/TTS.
4. Base de Conhecimento (RAG): Sempre que tiver dúvidas sobre regras de negócio, playbooks dos arquétipos, schemas ou arquitetura do sistema operacional, use a ferramenta `search_knowledge_tool`.
5. Governança & Segurança: Todas as ações de alto impacto requerem transparência. Entregáveis como roteiros de alta retenção ou propostas de campanha devem ser submetidas à Supervisão Humana via `submit_to_approval_queue`.
{biz_context}
{memories_str}
Responda sempre em português do Brasil com formatação markdown clara e executiva.
"""


async def call_gemini_generate_content(
    api_key: str,
    contents: list[dict[str, Any]],
    system_instruction: str,
    tools_declarations: list[dict[str, Any]],
    preferred_model: str = "gemini-3.8-flash",
) -> tuple[dict[str, Any], str]:
    """Chama a API do Gemini com fallback resiliente em caso de 503/429."""
    models_to_try = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]
    last_error = None

    tools_payload = [{"function_declarations": tools_declarations}]

    payload = {
        "contents": contents,
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "tools": tools_payload,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        },
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        for model in models_to_try:
            api_model = "gemini-3.8-flash" if model in ("gemini-3.8", "gemini-3.8-pro") else model
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent?key={api_key}"
            try:
                t0 = time.time()
                res = await client.post(url, json=payload)
                elapsed = int((time.time() - t0) * 1000)

                if res.status_code == 200:
                    data = res.json()
                    logger.info(f"Gemini call success with model {model} ({elapsed}ms)")
                    return data, model
                elif res.status_code in (503, 429):
                    logger.warning(f"Model {model} indisponível ({res.status_code}). Tentando fallback...")
                    last_error = f"HTTP {res.status_code}: {res.text[:120]}"
                    continue
                else:
                    logger.error(f"Gemini API error ({res.status_code}): {res.text[:200]}")
                    last_error = f"HTTP {res.status_code}: {res.text[:200]}"
                    continue
            except Exception as e:
                logger.warning(f"Erro ao chamar {model}: {e}")
                last_error = str(e)
                continue

    raise RuntimeError(f"Falha ao conectar aos modelos do Gemini. Último erro: {last_error}")


class JeffreyOrchestrator:
    def __init__(self, conversation: AgentConversation, db: AsyncSession):
        self.conversation = conversation
        self.db = db
        self.user = getattr(conversation, "user", None)
        self.business = getattr(conversation, "business", None)

    async def execute_turn(self, user_message_text: str) -> tuple[AgentMessage, list[AgentMessage]]:
        """Executa o turno do usuário no ciclo ReAct completo."""
        now = _utc_now()
        created_messages: list[AgentMessage] = []

        # Garante carregamento assíncrono seguro de user e business sem lazy load
        if not self.user and self.conversation.user_id:
            u_res = await self.db.execute(select(User).where(User.id == self.conversation.user_id))
            self.user = u_res.scalar_one_or_none()
        if not self.business and self.conversation.business_id:
            b_res = await self.db.execute(select(Business).where(Business.id == self.conversation.business_id))
            self.business = b_res.scalar_one_or_none()

        # 1. Salva mensagem do usuário
        user_msg = AgentMessage(
            agent_conversation_id=self.conversation.id,
            role="user",
            content=user_message_text,
            created_at=now,
            updated_at=now,
        )
        self.db.add(user_msg)
        await self.db.flush()
        created_messages.append(user_msg)

        # 2. Carrega memórias e monta system prompt
        memories = await get_contextual_memories(
            self.db,
            user_id=self.user.id,
            business_id=self.conversation.business_id,
            limit=8,
        )
        memories_str = format_memories_prompt(memories)
        system_instruction = build_system_instruction(self.user, self.business, memories_str)

        # 3. Recupera histórico recente de mensagens (Short-Term Memory)
        hist_res = await self.db.execute(
            select(AgentMessage)
            .where(AgentMessage.agent_conversation_id == self.conversation.id)
            .order_by(AgentMessage.id.asc())
        )
        all_db_msgs = hist_res.scalars().all()

        # Monta payload `contents` para a API
        contents: list[dict[str, Any]] = []
        for m in all_db_msgs:
            if m.role == "user" and m.content:
                contents.append({"role": "user", "parts": [{"text": m.content}]})
            elif m.role in ("model", "assistant") and m.content:
                contents.append({"role": "model", "parts": [{"text": m.content}]})

        api_key = await get_effective_gemini_key(self.user, self.db)
        tools_declarations = get_gemini_tools_declarations()
        preferred_model = settings.GEMINI_MODEL or "gemini-3.8-flash"

        # 4. Ciclo ReAct Loop
        step = 0
        final_text = ""
        last_model_used = preferred_model
        total_prompt_tokens = 0
        total_completion_tokens = 0

        while step < MAX_REACT_STEPS:
            step += 1
            t_start = time.time()
            current_preferred = last_model_used if step > 1 else preferred_model
            try:
                response_data, last_model_used = await call_gemini_generate_content(
                    api_key=api_key,
                    contents=contents,
                    system_instruction=system_instruction,
                    tools_declarations=tools_declarations,
                    preferred_model=current_preferred,
                )
            except Exception as e:
                logger.error(f"Erro no ReAct loop na iteração {step}: {e}")
                final_text = f"Olá, sou o Jeffrey. Encontrei uma oscilação na conexão com a IA, mas seus dados e operações continuam preservados. Detalhe: {str(e)[:150]}"
                break

            latency_ms = int((time.time() - t_start) * 1000)

            # Acumula uso de tokens
            usage_meta = response_data.get("usageMetadata", {})
            total_prompt_tokens += usage_meta.get("promptTokenCount", 150)
            total_completion_tokens += usage_meta.get("candidatesTokenCount", 250)

            candidates = response_data.get("candidates", [])
            if not candidates:
                final_text = "Compreendido. Qual o próximo passo da nossa operação?"
                break

            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])

            # Procura chamadas de função
            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]

            if not function_calls:
                # O modelo respondeu com texto final
                text_parts = [p.get("text", "") for p in parts if "text" in p]
                final_text = "\n".join(text_parts).strip()
                break

            # Registra mensagem parcial do modelo com a chamada de ferramenta
            contents.append({
                "role": "model",
                "parts": parts,
            })

            # Executa cada function call detectada
            for call in function_calls:
                fn_name = call.get("name")
                fn_args = call.get("args", {})

                # Auditoria em AgentLog
                meta_info = TOOL_METADATA.get(fn_name, {})
                log_entry = AgentLog(
                    user_id=self.user.id,
                    business_id=self.conversation.business_id,
                    agent_conversation_id=self.conversation.id,
                    level="info",
                    event="tool_execution",
                    message=f"Jeffrey executou a tool '{fn_name}'",
                    context={"tool": fn_name, "args": fn_args, "title": meta_info.get("title")},
                    duration_ms=latency_ms,
                    created_at=_utc_now(),
                )
                self.db.add(log_entry)

                # Executa a tool
                tool_t0 = time.time()
                tool_result = await execute_agent_tool(
                    tool_name=fn_name,
                    tool_args=fn_args,
                    user_id=self.user.id,
                    db=self.db,
                )
                tool_duration_ms = int((time.time() - tool_t0) * 1000)

                # Salva mensagem de tool no banco
                tool_msg = AgentMessage(
                    agent_conversation_id=self.conversation.id,
                    role="tool",
                    tool_name=fn_name,
                    tool_args=fn_args,
                    tool_result=tool_result,
                    tool_failed="error" in tool_result,
                    latency_ms=tool_duration_ms,
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
                self.db.add(tool_msg)
                await self.db.flush()
                created_messages.append(tool_msg)

                # Injeta a function response de volta no array contents (role: 'user' conforme API do Gemini)
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": fn_name,
                            "response": tool_result,
                        }
                    }]
                })

        # 5. Salva resposta final do modelo
        now = _utc_now()
        assistant_msg = AgentMessage(
            agent_conversation_id=self.conversation.id,
            role="model",
            content=final_text or "Operação concluída pelo Jeffrey.",
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            created_at=now,
            updated_at=now,
        )
        self.db.add(assistant_msg)
        created_messages.append(assistant_msg)

        # 6. Atualiza conversa e auditoria
        self.conversation.messages_count = (self.conversation.messages_count or 0) + len(created_messages)
        self.conversation.model = last_model_used
        self.conversation.last_message_at = now
        self.conversation.updated_at = now

        total_tokens = total_prompt_tokens + total_completion_tokens
        usage_log = AiUsageLog(
            user_id=self.user.id,
            business_id=self.conversation.business_id,
            agent_conversation_id=self.conversation.id,
            model=last_model_used,
            context="react_chat",
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=Decimal(str(round(total_tokens * 0.0000003, 6))),
            latency_ms=latency_ms,
            created_at=now,
            updated_at=now,
        )
        self.db.add(usage_log)

        self.user.tokens_used_this_month = (self.user.tokens_used_this_month or 0) + total_tokens

        await self.db.commit()
        await self.db.refresh(assistant_msg)

        return assistant_msg, created_messages

