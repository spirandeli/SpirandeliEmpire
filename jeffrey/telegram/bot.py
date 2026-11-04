"""
SpirandeliEmpire OS - Jeffrey Telegram Bot
Bot para conversar com o Jeffrey diretamente pelo Telegram.

Fluxo:
  Usuário -> Telegram -> Bot (este arquivo) -> API Laravel (/jeffrey/chat) -> Jeffrey (AI Gateway) -> Resposta
"""
import os
import asyncio
import logging
import httpx
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [JEFFREY-TELEGRAM] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("JeffreyTelegramBot")

# ---------------------------------------------------------------------------
# Configuration via environment variables
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]

# IDs de Telegram autorizados (separe por vírgula no .env)
# Ex: TELEGRAM_ALLOWED_IDS=123456789,987654321
_raw_ids = os.getenv("TELEGRAM_ALLOWED_IDS", "")
ALLOWED_IDS: set[int] = {int(i.strip()) for i in _raw_ids.split(",") if i.strip().isdigit()}

# URL interna da API Laravel do Jeffrey
JEFFREY_API_URL: str = os.getenv("JEFFREY_API_URL", "http://core-app/api/v1/jeffrey/chat")
INTERNAL_API_SECRET: str = os.getenv("INTERNAL_API_SECRET", "")

# Provider de IA padrão para requisições vindas do Telegram
DEFAULT_AI_PROVIDER: str = os.getenv("TELEGRAM_AI_PROVIDER", "hybrid")

# Timeout para a chamada à API
API_TIMEOUT: float = float(os.getenv("TELEGRAM_API_TIMEOUT", "60"))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_authorized(user_id: int) -> bool:
    """Retorna True se o usuário está na lista de autorizados (ou se a lista está vazia = modo aberto)."""
    if not ALLOWED_IDS:
        return True
    return user_id in ALLOWED_IDS


async def _call_jeffrey(message: str, provider: str = DEFAULT_AI_PROVIDER) -> dict:
    """Chama a API interna do Jeffrey e retorna o dict de resposta."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if INTERNAL_API_SECRET:
        headers["X-Internal-Secret"] = INTERNAL_API_SECRET

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        resp = await client.post(
            JEFFREY_API_URL,
            json={"message": message, "provider": provider},
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()


def _format_reply(data: dict) -> str:
    """Formata a resposta do Jeffrey para exibição no Telegram."""
    reply = data.get("reply", "Sem resposta do Jeffrey.")
    model = data.get("model", "?")
    provider_name = data.get("provider_name", data.get("provider", "?"))
    latency = data.get("latency_ms", 0)
    fallback = data.get("fallback_used", False)
    budget = data.get("budget_status", {})

    footer_parts = [f"🤖 *{provider_name}* `{model}`  ⏱ {latency}ms"]
    if fallback:
        footer_parts.append("⚡ _fallback ativo_")
    if budget:
        spent = budget.get("current_spent_brl", 0)
        limit = budget.get("monthly_limit_brl", 200)
        pct = round(spent / limit * 100, 1) if limit else 0
        footer_parts.append(f"💰 R$ {spent:.2f} / R$ {limit:.2f} ({pct}%)")

    footer = "\n\n" + " · ".join(footer_parts)
    return reply + footer


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_authorized(user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    text = (
        f"Olá, *{user.first_name}*! Sou o *Jeffrey*, o agente central do *SpirandeliEmpire OS*.\n\n"
        "Pode me enviar qualquer mensagem e eu responderei com postura executiva e estratégica.\n\n"
        "Comandos disponíveis:\n"
        "  /start — Esta mensagem\n"
        "  /status — Status do orçamento e sistema\n"
        "  /memoria — Memórias operacionais ativas\n"
        "  /aprovacoes — Aprovações pendentes\n"
        "  /ajuda — Ajuda completa"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        data = await _call_jeffrey("Faça um relatório rápido do status operacional do sistema: orçamento, provedores de IA ativos e saúde geral.")
        await update.message.reply_text(_format_reply(data), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Erro ao consultar status: {e}")
        await update.message.reply_text(f"❌ Erro ao obter status: `{e}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_memoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            base = JEFFREY_API_URL.replace("/jeffrey/chat", "")
            headers = {"Accept": "application/json"}
            if INTERNAL_API_SECRET:
                headers["X-Internal-Secret"] = INTERNAL_API_SECRET
            resp = await client.get(f"{base}/jeffrey/memories", headers=headers)
            resp.raise_for_status()
            memories = resp.json()

        if not memories:
            await update.message.reply_text("📭 Nenhuma memória operacional ativa no momento.")
            return

        lines = ["*📋 Memórias Operacionais Ativas:*\n"]
        for m in memories[:20]:  # limita a 20 para não estourar a mensagem
            lines.append(f"• {m.get('content', '—')}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Erro ao buscar memórias: {e}")
        await update.message.reply_text(f"❌ Erro: `{e}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_aprovacoes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            base = JEFFREY_API_URL.replace("/jeffrey/chat", "")
            headers = {"Accept": "application/json"}
            if INTERNAL_API_SECRET:
                headers["X-Internal-Secret"] = INTERNAL_API_SECRET
            resp = await client.get(f"{base}/jeffrey/approvals", headers=headers)
            resp.raise_for_status()
            approvals = resp.json()

        if not approvals:
            await update.message.reply_text("✅ Nenhuma aprovação pendente.")
            return

        lines = [f"*⏳ {len(approvals)} aprovação(ões) pendente(s):*\n"]
        for a in approvals[:10]:
            lines.append(
                f"• *#{a.get('id')}* — {a.get('description', 'sem descrição')}"
                f"\n   Tipo: `{a.get('action_type', '?')}` | Risco: `{a.get('risk_level', '?')}`"
            )
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Erro ao buscar aprovações: {e}")
        await update.message.reply_text(f"❌ Erro: `{e}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update.effective_user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    text = (
        "*Jeffrey — Agente Central do SpirandeliEmpire OS*\n\n"
        "*Comandos:*\n"
        "  /start — Boas-vindas\n"
        "  /status — Status operacional e orçamento\n"
        "  /memoria — Memórias ativas do Jeffrey\n"
        "  /aprovacoes — Aprovações pendentes\n"
        "  /ajuda — Esta mensagem\n\n"
        "*Como usar:*\n"
        "Basta enviar qualquer mensagem de texto e o Jeffrey responderá. "
        "Você pode incluir o provider no início usando `[gemini]`, `[openai]` ou `[local]`.\n\n"
        "_Exemplo:_ `[gemini] Quais são as prioridades desta semana?`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ---------------------------------------------------------------------------
# Message handler — chat principal
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not _is_authorized(user.id):
        await update.message.reply_text("⛔ Acesso não autorizado.")
        return

    text: str = update.message.text.strip()
    if not text:
        return

    # Detecta provider inline: [gemini], [openai], [local]
    provider = DEFAULT_AI_PROVIDER
    for tag, prov in [("[gemini]", "gemini"), ("[openai]", "openai"), ("[local]", "ollama"), ("[llama]", "ollama")]:
        if text.lower().startswith(tag):
            provider = prov
            text = text[len(tag):].strip()
            break

    logger.info(f"Mensagem de @{user.username} (id={user.id}) | provider={provider}: {text[:80]}")

    # Mostra "digitando..." enquanto processa
    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        data = await _call_jeffrey(text, provider=provider)
        reply_text = _format_reply(data)

        # Telegram limita mensagens a 4096 chars
        if len(reply_text) > 4000:
            chunks = [reply_text[i : i + 4000] for i in range(0, len(reply_text), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling Jeffrey API: {e}")
        await update.message.reply_text(
            f"❌ Erro HTTP ao chamar o Jeffrey: `{e.response.status_code}`\n`{e.response.text[:200]}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except httpx.RequestError as e:
        logger.error(f"Request error calling Jeffrey API: {e}")
        await update.message.reply_text(
            "❌ Não consegui alcançar o backend do Jeffrey. Verifique se o serviço está online.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        await update.message.reply_text(f"❌ Erro inesperado: `{e}`", parse_mode=ParseMode.MARKDOWN)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def post_init(app: Application) -> None:
    """Registra os comandos no menu do Telegram."""
    await app.bot.set_my_commands([
        BotCommand("start", "Boas-vindas e introdução"),
        BotCommand("status", "Status operacional e orçamento"),
        BotCommand("memoria", "Memórias operacionais ativas"),
        BotCommand("aprovacoes", "Aprovações pendentes"),
        BotCommand("ajuda", "Ajuda completa"),
    ])
    logger.info("Bot commands registered.")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não definido. Configure no .env.")

    logger.info("Starting Jeffrey Telegram Bot...")
    if ALLOWED_IDS:
        logger.info(f"Access restricted to user IDs: {ALLOWED_IDS}")
    else:
        logger.warning("TELEGRAM_ALLOWED_IDS not set — bot is open to anyone!")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Registra handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("memoria", cmd_memoria))
    app.add_handler(CommandHandler("aprovacoes", cmd_aprovacoes))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Jeffrey Telegram Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

