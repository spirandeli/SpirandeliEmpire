"""
SpirandeliEmpire OS - Jeffrey Orchestrator Daemon Worker
Central autonomous background agent, task processor, real-time web researcher,
and multi-provider AI coordinator (Google Gemini, OpenAI, Local Ollama).
"""
import os
import re
import sys
import time
import json
import html
import logging
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import httpx
import redis

# Ensure root jeffrey package is importable
BASE_JEFFREY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_JEFFREY_DIR)

from permissions.gatekeeper import Gatekeeper, GatekeeperViolation
from memory.memory_manager import MemoryManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [JEFFREY-ORCHESTRATOR] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Jeffrey")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

MONTHLY_BUDGET_LIMIT = float(os.getenv("MONTHLY_BUDGET_LIMIT_BRL", 200.00))
AI_PROVIDER = os.getenv("AI_PROVIDER", "hybrid")

# --- AI PROVIDERS CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
raw_gemini_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").strip().rstrip("/")
if "generativelanguage" not in raw_gemini_url:
    raw_gemini_url = "https://generativelanguage.googleapis.com/v1beta"
elif not raw_gemini_url.endswith("/v1beta") and not raw_gemini_url.endswith("/v1"):
    raw_gemini_url += "/v1beta"
GEMINI_BASE_URL = raw_gemini_url

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", os.getenv("DEFAULT_TEXT_MODEL", "qwen2.5:3b"))

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/app/storage")

QUEUE_KEYS = [
    "empire:jeffrey:tasks",
    "spirandeli_database_empire:jeffrey:tasks",
    "laravel_database_empire:jeffrey:tasks",
]

memory_manager = MemoryManager()


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        decode_responses=True
    )


def get_db_connection():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        database=os.getenv("DB_DATABASE", "spirandeli_empire"),
        user=os.getenv("DB_USERNAME", "empire_admin"),
        password=os.getenv("DB_PASSWORD", ""),
        connect_timeout=5
    )


def _resolve_ollama_model(requested_model: Optional[str] = None) -> str:
    """Inspect installed Ollama models and always prioritize 3b/1.5b models to prevent 8GB VPS OOM crashes."""
    target = requested_model or LLAMA_MODEL
    if re.search(r":(7b|8b|13b|14b)", target or "", flags=re.I):
        target = "qwen2.5:3b"
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=4.0)
        if r.status_code == 200:
            models = r.json().get("models", [])
            installed = [m.get("name") for m in models if m.get("name")]
            if not installed:
                return target
            for preferred in ("qwen2.5:3b", "llama3.2:3b", "qwen2.5:1.5b", "llama3.2:1b"):
                if preferred in installed:
                    if target == preferred or target not in installed or re.search(r":(7b|8b|13b|14b)", target, flags=re.I):
                        return preferred
            if target in installed:
                return target
            return installed[0]
    except Exception:
        pass
    return target


def test_ai_connections() -> bool:
    """Verify connectivity to all configured AI providers."""
    if GEMINI_API_KEY:
        try:
            url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"role": "user", "parts": [{"text": "ping"}]}]}
            res = httpx.post(url, json=payload, timeout=8.0)
            if res.status_code == 200:
                logger.info(f"Google Gemini connected successfully. Model: {GEMINI_MODEL}")
            else:
                logger.warning(f"Google Gemini returned HTTP {res.status_code}: {res.text[:100]}")
        except Exception as e:
            logger.warning(f"Google Gemini connection check failed: {e}")
    else:
        logger.info("Google Gemini key not configured (GEMINI_API_KEY empty).")

    if OPENAI_API_KEY:
        try:
            url = f"{OPENAI_BASE_URL}/chat/completions"
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
            payload = {
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }
            res = httpx.post(url, headers=headers, json=payload, timeout=8.0)
            if res.status_code == 200:
                logger.info(f"OpenAI connected successfully. Model: {OPENAI_MODEL}")
            else:
                logger.warning(f"OpenAI returned HTTP {res.status_code}: {res.text[:100]}")
        except Exception as e:
            logger.warning(f"OpenAI connection check failed: {e}")
    else:
        logger.info("OpenAI key not configured (OPENAI_API_KEY empty).")

    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if r.status_code == 200:
            models = r.json().get("models", [])
            model_names = [m.get("name") for m in models]
            resolved = _resolve_ollama_model()
            logger.info(f"Local Ollama AI service connected. Installed: {model_names} | Active: {resolved}")
            return True
    except Exception as e:
        logger.warning(f"Ollama connection check pending: {e}")
    return False


def _get_active_api_keys() -> Tuple[str, str]:
    """
    Resolve active GEMINI_API_KEY and OPENAI_API_KEY from environment variables,
    falling back to dynamic configuration saved in Redis ('empire:ai:config') or PostgreSQL.
    """
    g_key = (GEMINI_API_KEY or "").strip()
    o_key = (OPENAI_API_KEY or "").strip()
    if len(g_key) > 10 and len(o_key) > 10:
        return g_key, o_key

    try:
        r = get_redis_client()
        raw = r.get("empire:ai:config")
        if raw:
            cfg = json.loads(raw)
            if len(g_key) <= 10 and cfg.get("gemini_api_key"):
                g_key = str(cfg["gemini_api_key"]).strip()
            if len(o_key) <= 10 and cfg.get("openai_api_key"):
                o_key = str(cfg["openai_api_key"]).strip()
    except Exception:
        pass

    if len(g_key) <= 10 and len(o_key) <= 10:
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM jeffrey_memories WHERE category = 'system_ai_keys' AND is_active = TRUE ORDER BY id DESC LIMIT 1"
                )
                row = cur.fetchone()
                if row and row[0]:
                    cfg = json.loads(row[0])
                    if len(g_key) <= 10 and cfg.get("gemini_api_key"):
                        g_key = str(cfg["gemini_api_key"]).strip()
                    if len(o_key) <= 10 and cfg.get("openai_api_key"):
                        o_key = str(cfg["openai_api_key"]).strip()
            conn.close()
        except Exception:
            pass

    return g_key, o_key


def _get_ai_availability_config() -> Dict[str, Any]:
    """Read AI availability & login access control configuration saved by Commander."""
    defaults = {
        "enabled_providers": {
            "ollama": True,
            "gemini": True,
            "openai": True,
            "hybrid": True,
        },
        "gemini_access_policy": "owner_only",
        "default_provider_for_others": "ollama",
    }
    try:
        r = get_redis_client()
        raw = r.get("empire:ai:config")
        if raw:
            cfg = json.loads(raw)
            if isinstance(cfg.get("enabled_providers"), dict):
                defaults["enabled_providers"].update(cfg["enabled_providers"])
            if cfg.get("gemini_access_policy"):
                defaults["gemini_access_policy"] = cfg["gemini_access_policy"]
            if cfg.get("default_provider_for_others"):
                defaults["default_provider_for_others"] = cfg["default_provider_for_others"]
    except Exception:
        pass
    return defaults


def query_gemini(prompt: str, system_prompt: Optional[str] = None, enable_google_search: bool = False) -> Optional[Dict[str, Any]]:
    g_key, _ = _get_active_api_keys()
    if len(g_key) <= 10:
        return None
    try:
        base_payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4096}
        }
        if system_prompt:
            base_payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        candidate_models = []
        if GEMINI_MODEL:
            candidate_models.append(GEMINI_MODEL)
        for fallback_m in ("gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.1-pro-preview", "gemini-2.5-flash"):
            if fallback_m not in candidate_models:
                candidate_models.append(fallback_m)

        start = time.time()
        res = None
        used_model = GEMINI_MODEL

        # Force IPv4 transport so broken Docker IPv6 routing on Linux VPS never causes 45s timeouts
        transport = httpx.HTTPTransport(local_address="0.0.0.0")
        with httpx.Client(transport=transport, timeout=httpx.Timeout(35.0, connect=8.0)) as client:
            for model_name in candidate_models:
                url = f"{GEMINI_BASE_URL}/models/{model_name}:generateContent?key={g_key}"
                model_retries = 3 if model_name == (GEMINI_MODEL or "gemini-3.8-flash") else 1

                for attempt_idx in range(1, model_retries + 1):
                    try:
                        attempt = client.post(url, json=base_payload)
                        if attempt.status_code == 200:
                            res = attempt
                            used_model = model_name
                            break
                        res = attempt
                        err_text = attempt.text
                        is_retryable = attempt.status_code in (404, 400, 429, 500, 502, 503, 504) or any(
                            term in err_text.lower() for term in ("high demand", "overloaded", "temporary", "quota", "rate")
                        )
                        if is_retryable:
                            if attempt_idx < model_retries:
                                wait_sec = attempt_idx * 1.4
                                logger.info(f"Gemini {model_name} pico temporario de demanda ({attempt.status_code}). Tentativa {attempt_idx}/{model_retries}. Aguardando {wait_sec}s...")
                                time.sleep(wait_sec)
                                continue
                            else:
                                logger.warning(f"Gemini {model_name} persistiu em alta demanda apos {model_retries} tentativas. Testando proximo modelo...")
                                time.sleep(0.4)
                                break
                        break
                    except Exception as inner_e:
                        clean_err = re.sub(r"key=[^&\s]+", "key=***", str(inner_e))
                        logger.warning(f"Gemini attempt on {model_name} failed: {clean_err}")
                        if attempt_idx < model_retries:
                            time.sleep(1.2)
                            continue
                        break
                if res is not None and res.status_code == 200:
                    break

        latency = int((time.time() - start) * 1000)

        if res is not None and res.status_code == 200:
            data = res.json()
            cand = (data.get("candidates") or [{}])[0]
            parts = (cand.get("content") or {}).get("parts") or []
            text_chunks = [p.get("text", "") for p in parts if p.get("text")]
            text = "\n".join(text_chunks).strip()

            if text:
                return {
                    "success": True,
                    "response": text,
                    "provider": "google_gemini",
                    "model": used_model,
                    "latency_ms": latency
                }
        elif res is not None:
            logger.warning(f"Gemini API returned error {res.status_code}: {res.text[:200]}")
    except Exception as e:
        clean_err = re.sub(r"key=[^&\s]+", "key=***", str(e))
        logger.error(f"Gemini execution failed: {clean_err}")
    return None


def query_openai(prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
    _, o_key = _get_active_api_keys()
    if len(o_key) <= 10:
        return None
    try:
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {o_key}"}
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        start = time.time()
        res = httpx.post(url, headers=headers, json=payload, timeout=45.0)
        latency = int((time.time() - start) * 1000)

        if res.status_code == 200:
            data = res.json()
            text = data["choices"][0]["message"]["content"]
            return {
                "success": True,
                "response": text,
                "provider": "openai",
                "model": OPENAI_MODEL,
                "latency_ms": latency
            }
        logger.warning(f"OpenAI API returned error {res.status_code}: {res.text[:200]}")
    except Exception as e:
        logger.error(f"OpenAI execution failed: {e}")
    return None


def query_ollama(prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
    target_model = _resolve_ollama_model()
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "num_ctx": 2048,
                "num_predict": 700,
                "temperature": 0.6,
            }
        }
        start = time.time()
        res = httpx.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=180.0)

        if res.status_code >= 500:
            logger.warning(f"Ollama /api/chat returned {res.status_code}, retrying with compact num_ctx=1024...")
            retry_payload = {
                "model": target_model,
                "prompt": prompt,
                "system": "Você é Jeffrey, agente executivo do SpirandeliEmpire OS. Responda em português brasileiro com dados práticos e objetivos.",
                "stream": False,
                "options": {"num_ctx": 1024, "num_predict": 500}
            }
            res = httpx.post(f"{OLLAMA_BASE_URL}/api/generate", json=retry_payload, timeout=180.0)

        latency = int((time.time() - start) * 1000)
        if res.status_code == 200:
            data = res.json()
            text = (data.get("message") or {}).get("content") or data.get("response", "")
            if text:
                return {
                    "success": True,
                    "response": text,
                    "provider": "ollama_llama",
                    "model": target_model,
                    "latency_ms": latency
                }
        logger.warning(f"Ollama returned HTTP {res.status_code}: {res.text[:200]}")
    except Exception as e:
        logger.error(f"Ollama local execution failed: {e}")
    return None


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text.strip()) / 3.6))


def _classify_task_role(prompt: str, task_type: str = "") -> str:
    """
    Classify whether a task is strictly Reading/Analysis ('read_analyze') -> Llama Local,
    or Task Execution ('execute_task') -> Google Gemini / OpenAI Chat.
    """
    if task_type in ("analysis", "read_analyze", "log_analysis", "triage"):
        return "read_analyze"
    low = (prompt or "").lower()
    is_exec = bool(re.search(r"\b(executar|execute|criar|crie|gerar|gere|roteiro|produzir|rodar|campanha|escrever|entreg|ciclo)\b", low))
    is_read = bool(re.search(r"\b(ler|leia|analisar|analise|análise|resumir|resuma|inspecionar|classificar|triagem)\b", low))
    if is_read and not is_exec:
        return "read_analyze"
    return "execute_task"


def _llama_read_and_analyze(raw_context: str, task_goal: str) -> Optional[Dict[str, Any]]:
    """
    Use Llama Local (Ollama) specifically to read and analyze raw context, web snippets,
    and business data before handing over to Gemini / OpenAI Chat for task execution.
    """
    if not raw_context or not raw_context.strip():
        return None
    analysis_system = (
        "Você é o Agente Analista Local (Llama) do SpirandeliEmpire OS. "
        "Sua função exclusiva é LER e ANALISAR os dados brutos fornecidos (pesquisas da web, métricas e contas do negócio) "
        "e extrair um resumo analítico objetivo em tópicos curtos para que o Agente Executor (Gemini/ChatGPT) execute a tarefa final."
    )
    analysis_prompt = (
        f"OBJETIVO DA MISSÃO: {task_goal[:300]}\n\n"
        f"DADOS BRUTOS PARA LEITURA E ANÁLISE:\n{raw_context[:4500]}\n\n"
        "Extraia em até 6 tópicos objetivos: (1) Principais produtos/tendências/fatos encontrados, "
        "(2) Contas e parâmetros do negócio aplicáveis, (3) Recomendações técnicas para a execução:"
    )
    return query_ollama(analysis_prompt, analysis_system)


def determine_optimal_provider(
    estimated_tokens: int,
    requested_provider: Optional[str] = None,
    task_role: str = "execute_task",
    allow_gemini: bool = True,
) -> Tuple[str, str]:
    g_key, o_key = _get_active_api_keys()
    avail_cfg = _get_ai_availability_config()
    enabled_provs = avail_cfg.get("enabled_providers", {})
    has_gemini = len(g_key) > 10 and bool(enabled_provs.get("gemini", True)) and allow_gemini
    has_openai = len(o_key) > 10 and bool(enabled_provs.get("openai", True))

    if requested_provider and requested_provider not in ("hybrid", "auto"):
        if requested_provider == "gemini" and not has_gemini:
            fallback_p = "openai" if has_openai else "ollama"
            return fallback_p, f"Acesso ao Gemini restrito ao login do Comandante ou desativado. Redirecionado para {fallback_p}."
        if requested_provider == "openai" and not has_openai:
            fallback_p = "gemini" if has_gemini else "ollama"
            return fallback_p, f"OpenAI desativado ou sem chave. Redirecionado para {fallback_p}."
        if requested_provider in ("ollama", "llama") and estimated_tokens > 6000 and has_gemini:
            return "gemini", f"Contexto de {estimated_tokens} tokens excede janela segura do Llama local. Delegado ao Gemini."
        return requested_provider, f"Provedor {requested_provider} requisitado explicitamente."

    # Cooperative Division when Gemini or OpenAI API Key is configured and permitted:
    # - Llama Local (Ollama) -> Read & Analyze ('read_analyze')
    # - Gemini or OpenAI Chat -> Execute Tasks ('execute_task')
    if has_gemini or has_openai:
        if task_role == "read_analyze" and estimated_tokens <= 6000:
            return "ollama", f"Modo Cooperativo: Tarefa de Leitura & Análise (~{estimated_tokens} tokens) atribuída ao Llama Local (Ollama)."
        if has_gemini:
            return "gemini", f"Modo Cooperativo: Execução de Tarefa (~{estimated_tokens} tokens) atribuída ao Google Gemini (após leitura/análise do Llama)."
        return "openai", f"Modo Cooperativo: Execução de Tarefa (~{estimated_tokens} tokens) atribuída ao OpenAI Chat (após leitura/análise do Llama)."

    return "ollama", f"Provedores cloud não disponíveis para este login; executando localmente no Ollama (~{estimated_tokens} tokens)."


def query_ai_engine(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: Optional[str] = None,
    task_role: str = "execute_task",
    allow_gemini: bool = True,
) -> Dict[str, Any]:
    """Execute AI inference with smart provider routing (Llama = Read/Analyze, Gemini/OpenAI = Execute) and full fallback chain."""
    full_text = prompt + (" " + system_prompt if system_prompt else "")
    est_tokens = estimate_tokens(full_text)
    optimal_prov, delegation_reason = determine_optimal_provider(est_tokens, provider, task_role, allow_gemini)
    g_key, o_key = _get_active_api_keys()
    avail_cfg = _get_ai_availability_config()
    enabled_provs = avail_cfg.get("enabled_providers", {})
    has_gemini = len(g_key) > 10 and bool(enabled_provs.get("gemini", True)) and allow_gemini
    has_openai = len(o_key) > 10 and bool(enabled_provs.get("openai", True))

    logger.info(f"Token analysis: ~{est_tokens} tokens | Role: [{task_role}] | Routing: [{optimal_prov}] | {delegation_reason}")
    prov = optimal_prov

    if prov == "gemini":
        res = query_gemini(prompt, system_prompt)
        if res:
            res["estimated_tokens"] = est_tokens
            res["delegation_reason"] = delegation_reason
            return res
        logger.warning("Gemini unavailable, falling back to OpenAI / Ollama...")
        if has_openai:
            openai_res = query_openai(prompt, system_prompt)
            if openai_res:
                openai_res["fallback_used"] = True
                openai_res["estimated_tokens"] = est_tokens
                return openai_res
        ollama_res = query_ollama(prompt, system_prompt)
        if ollama_res:
            ollama_res["fallback_used"] = True
            ollama_res["estimated_tokens"] = est_tokens
            return ollama_res

    elif prov == "openai":
        res = query_openai(prompt, system_prompt)
        if res:
            res["estimated_tokens"] = est_tokens
            res["delegation_reason"] = delegation_reason
            return res
        logger.warning("OpenAI unavailable, falling back to Gemini / Ollama...")
        if has_gemini:
            gemini_res = query_gemini(prompt, system_prompt)
            if gemini_res:
                gemini_res["fallback_used"] = True
                gemini_res["estimated_tokens"] = est_tokens
                return gemini_res
        ollama_res = query_ollama(prompt, system_prompt)
        if ollama_res:
            ollama_res["fallback_used"] = True
            ollama_res["estimated_tokens"] = est_tokens
            return ollama_res

    elif prov in ("ollama", "llama"):
        res = query_ollama(prompt, system_prompt)
        if res:
            res["estimated_tokens"] = est_tokens
            res["delegation_reason"] = delegation_reason
            return res
        if has_gemini:
            logger.warning("Local Ollama failed, falling back to Gemini...")
            gemini_res = query_gemini(prompt, system_prompt)
            if gemini_res:
                gemini_res["fallback_used"] = True
                gemini_res["estimated_tokens"] = est_tokens
                return gemini_res

    # Final hybrid sweep
    for fn in (query_gemini, query_openai, query_ollama):
        res = fn(prompt, system_prompt)
        if res:
            res["estimated_tokens"] = est_tokens
            return res

    return {
        "success": False,
        "error": "Nenhum provedor de IA disponível respondeu (verifique GEMINI_API_KEY, OPENAI_API_KEY ou o modelo no container empire_ollama)."
    }


# ============================================================================
# REAL-TIME WEB RESEARCH & EMPIRE CONTEXT TOOLS FOR BACKGROUND AGENTS
# ============================================================================

def _clean_search_query(raw_prompt: str) -> str:
    """Strip conversational task instructions and verbs so search engines get high-precision keywords."""
    q = re.sub(r"^(execute de forma completa.*?:|execute o ciclo.*?:)\s*", "", raw_prompt or "", flags=re.I | re.S)
    q = q.split("\n")[0].strip()
    # Remove conversational filler prefixes in Portuguese
    q = re.sub(
        r"\b(identificar|identifique|listar|liste|pesquisar|pesquise|buscar|busque|encontrar|encontre|"
        r"fazer um levantamento|faça um levantamento|me de|me dê|quero|preciso de|quais são|quais os|"
        r"os \d+|as \d+|\d+ melhores|\d+ principais)\b",
        " ",
        q,
        flags=re.I
    )
    q = re.sub(r"\btiktokshop\b", "TikTok Shop Brasil", q, flags=re.I)
    q = re.sub(r"\bviralizados\b", "virais mais vendidos", q, flags=re.I)
    q = re.sub(r"\s+", " ", q).strip(" -:,.?!")
    return q[:110] if len(q) >= 3 else (raw_prompt or "")[:100].strip()


def _decode_search_redirect_url(raw_url: str) -> str:
    """Unwrap DuckDuckGo (uddg=) or Yahoo (RU=...) redirect URLs into clean direct URLs."""
    u = html.unescape(raw_url or "").strip()
    if "uddg=" in u:
        m = re.search(r"[?&]uddg=([^&]+)", u)
        if m:
            return urllib.parse.unquote(m.group(1))
    if "/RU=" in u:
        m = re.search(r"/RU=([^/]+)/RK=", u)
        if m:
            return urllib.parse.unquote(m.group(1))
    if u.startswith("//"):
        return "https:" + u
    return u


def _fetch_page_excerpt(url: str) -> str:
    """Fetch a live web page and extract its meta description and key paragraph text."""
    if not url or not url.startswith("http") or any(x in url for x in ("youtube.com", "tiktok.com/search", ".pdf")):
        return ""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        resp = httpx.get(url, headers=headers, timeout=4.5, follow_redirects=True)
        if resp.status_code != 200 or "text/html" not in resp.headers.get("content-type", "").lower():
            return ""
        body = resp.text[:90000]
        body = re.sub(r"<(script|style|noscript|svg|header|footer|nav)[^>]*>.*?</\1>", " ", body, flags=re.I | re.S)
        meta_m = re.search(r'<meta[^>]+(?:name="description"|property="og:description")[^>]+content="([^"]+)"', body, re.I)
        meta_desc = html.unescape(meta_m.group(1)).strip() if meta_m else ""
        paragraphs = re.findall(r"<(?:p|li|h2|h3)[^>]*>(.*?)</(?:p|li|h2|h3)>", body, flags=re.I | re.S)
        clean_paras = []
        for p in paragraphs:
            txt = re.sub(r"<[^>]+>", " ", html.unescape(p))
            txt = re.sub(r"\s+", " ", txt).strip()
            if len(txt) > 45 and not any(skip in txt.lower() for skip in ("cookies", "política de privacidade", "todos os direitos")):
                clean_paras.append(txt)
            if len(" ".join(clean_paras)) > 550:
                break
        combined = (meta_desc + " | " + " ".join(clean_paras)).strip(" |")
        return combined[:650]
    except Exception:
        return ""


def _search_ecommerce_brazil_live(query: str, max_items: int = 8) -> List[Dict[str, str]]:
    """
    Fetch real products, real prices (R$), and real purchase/search URLs from Brazilian e-commerce
    (Mercado Livre Brasil API / Listing + TikTok Search discovery link) so product tasks never invent fake links.
    """
    items: List[Dict[str, str]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }
    # Determine high-converting product search terms if the query is generic "produtos virais tiktok shop"
    low_q = query.lower()
    if any(k in low_q for k in ("tiktok", "viral", "virais", "vendidos", "afiliado")):
        product_queries = [
            "mini processador eletrico usb",
            "escova secadora alisadora",
            "umidificador difusor led",
            "fone bluetooth tws",
            "projetor portatil smart",
            "massageador eletrico portatil",
            "luminaria led sensor movimento",
            "garrafa termica digital led",
            "kit skincare facial serum",
            "aparador pelos eletrico",
        ]
    else:
        product_queries = [query]

    # 1. Try Mercado Livre public search API
    for pq in product_queries[:5]:
        if len(items) >= max_items:
            break
        try:
            api_url = f"https://api.mercadolibre.com/sites/MLB/search?q={urllib.parse.quote(pq)}&limit=3"
            r = httpx.get(api_url, headers=headers, timeout=5.0)
            if r.status_code == 200:
                for prod in (r.json().get("results") or [])[:2]:
                    title = prod.get("title")
                    price = prod.get("price")
                    permalink = prod.get("permalink")
                    sold_qty = prod.get("sold_quantity")
                    if title and price and permalink:
                        tiktok_search_url = f"https://www.tiktok.com/search?q={urllib.parse.quote(title[:45])}"
                        sold_info = f" | +{sold_qty} vendidos" if sold_qty else ""
                        items.append({
                            "title": f"[Produto Real Brasil] {title} — R$ {float(price):.2f}",
                            "url": permalink,
                            "snippet": (
                                f"Preço Real Verificado: R$ {float(price):.2f}{sold_info} | "
                                f"Link Mercado Livre: {permalink} | "
                                f"Link Vídeos Virais no TikTok: {tiktok_search_url}"
                            ),
                        })
        except Exception:
            pass

    # 2. Fallback: scrape lista.mercadolivre.com.br HTML if API returned 403 on VPS IP
    if len(items) < 4:
        for pq in product_queries[:4]:
            if len(items) >= max_items:
                break
            try:
                slug = re.sub(r"[^a-zA-Z0-9]+", "-", pq.lower()).strip("-")
                list_url = f"https://lista.mercadolivre.com.br/{slug}"
                r = httpx.get(list_url, headers=headers, timeout=6.0, follow_redirects=True)
                if r.status_code == 200:
                    matches = re.findall(
                        r'<a[^>]+href="(https://(?:produto|www)\.mercadolivre\.com\.br/[^"#?]+)"[^>]*>(.*?)</a>',
                        r.text,
                        flags=re.I | re.S
                    )
                    prices = re.findall(r'class="andes-money-amount__fraction"[^>]*>([\d\.]+)<', r.text)
                    p_idx = 0
                    seen_titles = set()
                    for href, raw_t in matches:
                        clean_t = re.sub(r"<[^>]+>", "", html.unescape(raw_t)).strip()
                        if len(clean_t) < 12 or clean_t.lower() in seen_titles:
                            continue
                        seen_titles.add(clean_t.lower())
                        price_str = f"R$ {prices[p_idx]},00" if p_idx < len(prices) else "Consultar no link"
                        p_idx += 1
                        tiktok_search_url = f"https://www.tiktok.com/search?q={urllib.parse.quote(clean_t[:45])}"
                        items.append({
                            "title": f"[Produto Real E-commerce Brasil] {clean_t} ({price_str})",
                            "url": href,
                            "snippet": (
                                f"Preço Verificado: {price_str} | "
                                f"Link Real do Produto: {href} | "
                                f"Busca de Criadores/Vídeos no TikTok: {tiktok_search_url}"
                            ),
                        })
                        if len(items) >= max_items:
                            break
            except Exception:
                pass

    return items[:max_items]


def _web_search_live(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    Perform multi-engine zero-cost live web search resilient to VPS datacenter IP blocks:
      1. Bing Web Search RSS (works globally on VPS IPs without CAPTCHA)
      2. Yahoo Brasil Web Search (organic PT-BR web search)
      3. DuckDuckGo HTML / Lite (with uddg= redirect decoding)
      4. Google News RSS (PT-BR news & market trends)
      5. Live Brazilian E-Commerce product & price discovery (when searching products/TikTok Shop)
      6. Deep Page Reader on top URLs for rich article context
    """
    clean_q = _clean_search_query(query)
    results: List[Dict[str, str]] = []
    seen_urls = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def _add_result(title: str, url: str, snippet: str) -> None:
        real_url = _decode_search_redirect_url(url)
        if not title or not real_url or not real_url.startswith("http"):
            return
        if real_url in seen_urls:
            return
        seen_urls.add(real_url)
        results.append({
            "title": re.sub(r"\s+", " ", title).strip(),
            "url": real_url,
            "snippet": re.sub(r"\s+", " ", snippet or "").strip(),
        })

    # 1. Bing Web Search RSS (PT-BR)
    try:
        bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(clean_q)}&format=rss&setlang=pt-BR&cc=BR"
        resp = httpx.get(bing_url, headers=headers, timeout=8.0, follow_redirects=True)
        if resp.status_code == 200 and "<item>" in resp.text:
            items = re.findall(
                r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<description>(.*?)</description>.*?</item>",
                resp.text,
                re.S
            )
            for raw_t, link, desc in items[:max_results]:
                t_clean = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>|<[^>]+>", "", raw_t)).strip()
                d_clean = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>|<[^>]+>", "", desc)).strip()
                _add_result(t_clean, link.strip(), d_clean)
    except Exception as e:
        logger.debug(f"Bing RSS search note: {e}")

    # 2. Yahoo Brasil Web Search (PT-BR)
    if len(results) < max_results:
        try:
            yahoo_url = f"https://br.search.yahoo.com/search?p={urllib.parse.quote(clean_q)}&ei=UTF-8"
            resp = httpx.get(yahoo_url, headers=headers, timeout=8.0, follow_redirects=True)
            if resp.status_code == 200:
                blocks = re.findall(
                    r'<div[^>]+class="[^"]*algo-sr[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</li>',
                    resp.text,
                    re.S
                )
                for blk in blocks[:max_results]:
                    a_m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
                    s_m = re.search(r'<div[^>]+class="[^"]*compText[^"]*"[^>]*>(.*?)</div>', blk, re.S)
                    if a_m:
                        raw_href, raw_title = a_m.group(1), a_m.group(2)
                        t_clean = re.sub(r"<[^>]+>", " ", html.unescape(raw_title)).strip()
                        s_clean = re.sub(r"<[^>]+>", " ", html.unescape(s_m.group(1))).strip() if s_m else ""
                        _add_result(t_clean, raw_href, s_clean)
        except Exception as e:
            logger.debug(f"Yahoo BR search note: {e}")

    # 3. DuckDuckGo HTML Search
    if len(results) < max_results:
        try:
            resp = httpx.post(
                "https://html.duckduckgo.com/html/",
                data={"q": clean_q, "kl": "br-pt"},
                headers=headers,
                timeout=8.0,
                follow_redirects=True,
            )
            if resp.status_code == 200 and "result__a" in resp.text:
                body = resp.text
                titles = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body, re.S)
                snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', body, re.S)
                for idx, (href, raw_title) in enumerate(titles[:max_results]):
                    clean_title = re.sub(r"<[^>]+>", "", html.unescape(raw_title)).strip()
                    clean_snip = re.sub(r"<[^>]+>", "", html.unescape(snippets[idx])).strip() if idx < len(snippets) else ""
                    _add_result(clean_title, href, clean_snip)
        except Exception as e:
            logger.debug(f"DuckDuckGo search note: {e}")

    # 4. Google News RSS (PT-BR)
    if len(results) < max_results:
        try:
            encoded_q = urllib.parse.quote(clean_q)
            rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            resp = httpx.get(rss_url, headers=headers, timeout=8.0, follow_redirects=True)
            if resp.status_code == 200:
                items = re.findall(r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>.*?</item>", resp.text, re.S)
                for raw_t, link, pub_date in items[:6]:
                    clean_t = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", raw_t)).strip()
                    _add_result(clean_t, link.strip(), f"Notícia/Tendência publicada em {pub_date.strip()}")
        except Exception as e:
            logger.debug(f"Google News RSS note: {e}")

    # 5. Enrich top 3 organic web URLs with live page excerpt so AI reads actual article content
    for item in results[:3]:
        excerpt = _fetch_page_excerpt(item["url"])
        if excerpt and len(excerpt) > len(item.get("snippet", "")):
            item["snippet"] = excerpt

    # 6. If query involves products, TikTok Shop, viral items, or affiliate sales, fetch real e-commerce products & prices
    low_q = f"{query} {clean_q}".lower()
    if any(k in low_q for k in ("tiktok", "produto", "viral", "virais", "afiliado", "loja", "shop", "vendido", "preço", "preco", "oferta")):
        ecom_items = _search_ecommerce_brazil_live(clean_q, max_items=8)
        for ec in ecom_items:
            _add_result(ec["title"], ec["url"], ec["snippet"])

    logger.info(f"Live Web Search completed for '{clean_q}': {len(results)} real sources collected.")
    return results[:max_results]


def _should_perform_web_search(task_type: str, agent_name: str, prompt: str) -> bool:
    """Detect if the task requires real-time web / market / product research."""
    combined = f"{task_type} {agent_name} {prompt}".lower()
    keywords = [
        "pesquis", "research", "tiktok", "produto", "viral", "tendência", "tendencia",
        "mercado", "nicho", "concorr", "amazon", "kdp", "youtube", "shorts", "busca",
        "identificar", "levantamento", "top 10", "top 5", "afiliado", "preço", "preco",
        "históri", "histori", "bíbli", "bibli", "referência", "referencia", "internet",
        "web", "notícia", "noticia", "atual", "hoje", "2025", "2026", "shop", "shopee"
    ]
    return any(kw in combined for kw in keywords)


def _load_agent_context_from_db(agent_name: str, business_id: Optional[Any] = None) -> Dict[str, Any]:
    """Fetch agent persona, active memories, business details, and real monthly spend from PostgreSQL."""
    ctx: Dict[str, Any] = {
        "agent_system_prompt": None,
        "agent_role": "Agente Especialista",
        "memories_block": "",
        "business_info": "",
        "business_slug": None,
        "current_month_spent_brl": 0.0,
    }

    # Fallback system prompts from JSON file
    try:
        prompts_file = os.path.join(BASE_JEFFREY_DIR, "prompts", "system_prompts.json")
        if os.path.exists(prompts_file):
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts_data = json.load(f)
            key = agent_name.lower().replace(" ", "_")
            if key in prompts_data:
                ctx["agent_system_prompt"] = prompts_data[key].get("prompt")
                ctx["agent_role"] = prompts_data[key].get("role", ctx["agent_role"])
    except Exception:
        pass

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Agent profile from DB
            cur.execute(
                "SELECT role, system_prompt, model FROM agents WHERE LOWER(name) = LOWER(%s) OR slug = LOWER(%s) LIMIT 1",
                (agent_name, agent_name.lower().replace(" ", "-"))
            )
            agent_row = cur.fetchone()
            if agent_row:
                ctx["agent_role"] = agent_row[0] or ctx["agent_role"]
                if agent_row[1]:
                    ctx["agent_system_prompt"] = agent_row[1]

            # 2. Active memories
            if business_id and str(business_id).isdigit():
                cur.execute(
                    "SELECT category, content FROM jeffrey_memories WHERE is_active = TRUE AND (business_id IS NULL OR business_id = %s) ORDER BY id DESC LIMIT 12",
                    (int(business_id),)
                )
            else:
                cur.execute(
                    "SELECT category, content FROM jeffrey_memories WHERE is_active = TRUE ORDER BY id DESC LIMIT 12"
                )
            mem_rows = cur.fetchall()
            if mem_rows:
                memories_list = [{"category": r[0], "content": r[1]} for r in mem_rows]
                ctx["memories_block"] = memory_manager.format_context_prompt(memories_list)

            # 3. Business context (including accounts & automation parameters)
            if business_id and str(business_id).isdigit():
                cur.execute(
                    "SELECT name, slug, category, description, budget_limit_brl, settings FROM businesses WHERE id = %s",
                    (int(business_id),)
                )
                b_row = cur.fetchone()
                if b_row:
                    ctx["business_slug"] = b_row[1]
                    b_settings = b_row[5] if isinstance(b_row[5], dict) else (json.loads(b_row[5]) if b_row[5] else {})
                    b_accounts = b_settings.get("accounts") or []
                    b_params = b_settings.get("automation_params") or {}
                    acc_lines = []
                    for acc in b_accounts:
                        if isinstance(acc, dict):
                            acc_lines.append(
                                f"{acc.get('platform', 'Conta')}: {acc.get('handle', '')} "
                                f"(ID: {acc.get('account_id', 'N/A')}, Link: {acc.get('affiliate_showcase_url', 'N/A')})"
                            )
                    acc_str = " | Contas Vinculadas: " + "; ".join(acc_lines) if acc_lines else ""
                    param_str = ""
                    if isinstance(b_params, dict) and b_params:
                        param_str = (
                            f" | Parâmetros do Negócio: Nicho={b_params.get('niche', '')}, "
                            f"Público={b_params.get('target_audience', '')}, "
                            f"Meta={b_params.get('daily_deliverables_goal', 3)}/dia, "
                            f"CTA='{b_params.get('cta_template', '')}', "
                            f"Regras='{b_params.get('custom_prompt_rules', '')}'"
                        )
                    ctx["business_info"] = (
                        f"Negócio em foco: {b_row[0]} ({b_row[2]}) — {b_row[3]} | Teto: R$ {b_row[4]}"
                        f"{acc_str}{param_str}"
                    )
            else:
                cur.execute("SELECT name, slug, category, status, settings FROM businesses WHERE status = 'active' LIMIT 6")
                b_rows = cur.fetchall()
                if b_rows:
                    b_summary = []
                    for r in b_rows:
                        s_dict = r[4] if isinstance(r[4], dict) else (json.loads(r[4]) if r[4] else {})
                        accs = s_dict.get("accounts") or []
                        handles = ", ".join([a.get("handle", "") for a in accs if isinstance(a, dict) and a.get("handle")])
                        b_summary.append(f"{r[0]} ({r[2]}{' - Contas: ' + handles if handles else ''})")
                    ctx["business_info"] = f"Negócios ativos no Império: {'; '.join(b_summary)}"

            # 4. Current month expenses for Gatekeeper
            cur.execute("""
                SELECT COALESCE(SUM(amount_brl), 0)
                FROM financial_records
                WHERE type != 'revenue'
                  AND recorded_at >= date_trunc('month', CURRENT_DATE)
            """)
            spent_row = cur.fetchone()
            if spent_row and spent_row[0] is not None:
                ctx["current_month_spent_brl"] = float(spent_row[0])

        conn.close()
    except Exception as e:
        logger.warning(f"Could not load extended DB context for task: {e}")

    return ctx


def _save_task_deliverable(task_id: str, title: str, content: str, business_slug: Optional[str] = None) -> Optional[str]:
    """Persist the completed agent deliverable to storage so the user has the file on disk."""
    try:
        folder = os.path.join(STORAGE_ROOT, "businesses", business_slug or "general", "output")
        os.makedirs(folder, exist_ok=True)
        safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", title.lower())[:50].strip("-") or "entrega"
        filename = f"task_{task_id}_{safe_slug}.md"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Tarefa #{task_id}: {title}\n")
            f.write(f"> Gerado em: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
            f.write(content)
        return filepath
    except Exception as e:
        logger.warning(f"Could not save deliverable file for task #{task_id}: {e}")
        return None


def _create_approval_request_in_db(agent_name: str, action_type: str, reason: str, task_id: str, business_id: Optional[Any], payload: Dict[str, Any]) -> None:
    """Create a real ApprovalRequest record in PostgreSQL when Gatekeeper requires human approval."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            b_id = int(business_id) if business_id and str(business_id).isdigit() else None
            cost = float(payload.get("estimated_cost_brl", 0.0))
            cur.execute("""
                INSERT INTO approval_requests (business_id, agent_name, action_type, description, risk_level, estimated_cost_brl, payload, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'high', %s, %s, 'pending', NOW(), NOW())
            """, (
                b_id,
                agent_name,
                action_type,
                f"Tarefa #{task_id}: {reason}",
                cost,
                json.dumps({"task_id": task_id, "original_payload": payload})
            ))
            conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not insert approval_request for task #{task_id}: {e}")


def _record_agent_decision(agent_name: str, business_id: Optional[Any], action_type: str, justification: str, payload: Dict[str, Any]) -> None:
    """Record background worker execution in agent_decisions table for live UI audit log."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            b_id = int(business_id) if business_id and str(business_id).isdigit() else None
            cur.execute("""
                INSERT INTO agent_decisions (agent_name, business_id, action_type, justification, input_payload, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'executed', NOW(), NOW())
            """, (
                agent_name,
                b_id,
                action_type,
                justification[:250],
                json.dumps(payload)
            ))
            conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not record agent_decision: {e}")


def _set_worker_state(r: redis.Redis, state: Dict[str, Any]) -> None:
    """Publish live worker state to Redis (both unprefixed and legacy prefixed keys)."""
    try:
        raw = json.dumps(state)
        r.set("empire:jeffrey:worker_state", raw, ex=180)
        r.set("spirandeli_database_empire:jeffrey:worker_state", raw, ex=180)
    except Exception:
        pass


def _publish_task_result(r: redis.Redis, task_id: str, result: Dict[str, Any]) -> None:
    """Publish task result back to Redis."""
    try:
        raw = json.dumps(result)
        r.set(f"empire:jeffrey:results:{task_id}", raw, ex=3600)
        r.publish("empire:jeffrey:results:channel", json.dumps({"task_id": task_id}))
    except Exception:
        pass


def _check_and_mark_db_task_in_progress(task_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if task exists in PostgreSQL and is eligible to run (not already cancelled/completed,
    and if it has depends_on_task_id, verify the parent task has finished).
    If eligible, mark it as in_progress and return (True, db_task_info).
    """
    if not str(task_id).isdigit():
        return True, None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status, title, type, agent_name, business_id, payload FROM tasks WHERE id = %s",
                (int(task_id),)
            )
            row = cur.fetchone()
            if not row:
                conn.close()
                logger.warning(f"Task #{task_id} no longer exists in DB. Skipping.")
                return False, None

            current_status = row[1]
            if current_status in ("cancelled", "completed"):
                conn.close()
                logger.info(f"Task #{task_id} is already [{current_status}] in DB. Skipping duplicate queue entry.")
                return False, None

            payload_val = row[6] if isinstance(row[6], dict) else (json.loads(row[6]) if row[6] else {})
            depends_on_id = payload_val.get("depends_on_task_id")

            # Check parent task dependency if this task is part of a chained pipeline
            if depends_on_id and str(depends_on_id).isdigit():
                cur.execute(
                    "SELECT status, title, result FROM tasks WHERE id = %s",
                    (int(depends_on_id),)
                )
                parent_row = cur.fetchone()
                if parent_row:
                    parent_status, parent_title, parent_res_raw = parent_row
                    if parent_status in ("pending", "in_progress"):
                        conn.close()
                        logger.info(f"Task #{task_id} is waiting for parent task #{depends_on_id} [{parent_status}] to complete.")
                        return False, None
                    if parent_status in ("failed", "cancelled"):
                        cur.execute(
                            """
                            UPDATE tasks
                            SET status = 'failed', error_message = %s, completed_at = NOW(), updated_at = NOW()
                            WHERE id = %s
                            """,
                            (f"Cancelada automaticamente pois a Tarefa anterior (#{depends_on_id}) terminou com status '{parent_status}'.", int(task_id))
                        )
                        conn.commit()
                        conn.close()
                        return False, None
                    if parent_status == "completed":
                        parent_res = parent_res_raw if isinstance(parent_res_raw, dict) else (json.loads(parent_res_raw) if parent_res_raw else {})
                        payload_val["parent_task_id"] = str(depends_on_id)
                        payload_val["parent_task_title"] = parent_title or f"Tarefa #{depends_on_id}"
                        payload_val["parent_task_output"] = (parent_res or {}).get("response", "")

            cur.execute("""
                UPDATE tasks
                SET status = 'in_progress', started_at = NOW(), error_message = NULL, updated_at = NOW()
                WHERE id = %s
            """, (int(task_id),))
            conn.commit()

            db_info = {
                "id": str(row[0]),
                "status": "in_progress",
                "title": row[2],
                "type": row[3],
                "agent_name": row[4] or "Jeffrey",
                "business_id": row[5],
                "payload": payload_val,
            }
        conn.close()
        logger.info(f"Task #{task_id} marked as [in_progress] in PostgreSQL.")
        return True, db_info
    except Exception as e:
        logger.warning(f"Could not check/mark task #{task_id} in_progress in PostgreSQL: {e}")
        return True, None


def _update_db_task_status(
    task_id: str,
    status: str,
    result: Dict[str, Any],
    error: Optional[str] = None,
    conversation_id: Optional[Any] = None,
    agent_name: str = "Jeffrey"
) -> None:
    """Update task record directly in PostgreSQL and post finished reply to conversation."""
    if not str(task_id).isdigit():
        return
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks 
                SET status = %s, result = %s, error_message = %s, completed_at = NOW(), updated_at = NOW()
                WHERE id = %s
                RETURNING title, payload
            """, (status, json.dumps(result), error, int(task_id)))
            row = cur.fetchone()
            task_title = row[0] if row else f"Tarefa #{task_id}"

            if not conversation_id and row and row[1]:
                p_data = row[1] if isinstance(row[1], dict) else (json.loads(row[1]) if isinstance(row[1], str) else {})
                conversation_id = p_data.get("conversation_id")

            # If still no conversation_id, post to latest conversation so Commander always sees the result
            if not conversation_id:
                cur.execute("SELECT id FROM conversations ORDER BY updated_at DESC LIMIT 1")
                conv_row = cur.fetchone()
                if conv_row:
                    conversation_id = conv_row[0]

            if conversation_id and str(conversation_id).isdigit():
                if status == "completed" and result.get("response"):
                    saved_note = f"\n\n📁 _Arquivo salvo em: `{result['saved_file']}`_" if result.get("saved_file") else ""
                    msg_content = f"✅ **[Tarefa #{task_id} Concluída — {agent_name}]:** _{task_title}_\n\n{result.get('response')}{saved_note}"
                else:
                    msg_content = f"⚠️ **[Tarefa #{task_id} Finalizada com Alerta — {agent_name}]:** _{task_title}_\nMotivo: {error or 'Sem resposta do provedor.'}"

                cur.execute("""
                    INSERT INTO messages (conversation_id, role, content, provider, model, latency_ms, fallback_used, created_at, updated_at)
                    VALUES (%s, 'assistant', %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    int(conversation_id),
                    msg_content,
                    result.get("provider") or "worker",
                    result.get("model") or "jeffrey-worker",
                    int(result.get("latency_ms") or 0),
                    bool(result.get("fallback_used", False))
                ))
                cur.execute("UPDATE conversations SET updated_at = NOW() WHERE id = %s", (int(conversation_id),))

            conn.commit()
        conn.close()
        logger.info(f"Task #{task_id} status updated to [{status}] in PostgreSQL.")
    except Exception as e:
        logger.warning(f"Could not update task #{task_id} in PostgreSQL: {e}")


def _recover_orphan_db_tasks() -> List[Dict[str, Any]]:
    """
    Find any tasks in PostgreSQL that are stuck in 'pending' (created > 3s ago)
    or stale 'in_progress' (started > 10m ago) and return them for immediate execution.
    """
    orphan_tasks: List[Dict[str, Any]] = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, type, agent_name, business_id, payload, estimated_cost_brl
                FROM tasks
                WHERE (status = 'pending' AND created_at <= NOW() - INTERVAL '3 seconds')
                   OR (status = 'in_progress' AND started_at <= NOW() - INTERVAL '10 minutes')
                ORDER BY id ASC
                LIMIT 5
            """)
            rows = cur.fetchall()
            for r in rows:
                raw_payload = r[5]
                payload_dict = raw_payload if isinstance(raw_payload, dict) else (json.loads(raw_payload) if raw_payload else {})
                if not payload_dict.get("prompt"):
                    payload_dict["prompt"] = r[1]
                payload_dict["estimated_cost_brl"] = float(r[6] or 0.0)
                orphan_tasks.append({
                    "id": str(r[0]),
                    "title": r[1],
                    "type": r[2] or "research",
                    "agent_name": r[3] or "Jeffrey",
                    "business_id": r[4],
                    "payload": payload_dict,
                })
        conn.close()
    except Exception as e:
        logger.warning(f"DB orphan task check warning: {e}")
    return orphan_tasks


def process_task(task: Dict[str, Any]) -> None:
    """
    Execute an incoming empire task as a full autonomous background agent:
      1. Verify DB task status (skip if cancelled/completed) & mark in_progress
      2. Load Agent Persona, Operational Memories & Monthly Spend from PostgreSQL
      3. Validate via Gatekeeper (and create ApprovalRequest in DB if human approval needed)
      4. Execute Real-Time Web Search / Empire Data gathering when applicable
      5. Query AI Engine with enriched context & agent persona
      6. Save deliverable artifact to disk & publish results to PostgreSQL + Redis + Conversation
    """
    task_id = str(task.get("id", f"task_{int(time.time())}"))

    should_run, db_info = _check_and_mark_db_task_in_progress(task_id)
    if not should_run:
        return

    if db_info:
        task_type = db_info.get("type") or task.get("type", "research")
        agent_name = db_info.get("agent_name") or task.get("agent_name", "Jeffrey")
        business_id = db_info.get("business_id") or task.get("business_id")
        payload = {**(db_info.get("payload") or {}), **(task.get("payload") or {})}
        task_title = db_info.get("title") or payload.get("prompt", task_type)[:80]
    else:
        task_type = task.get("type", "research")
        agent_name = task.get("agent_name", "Jeffrey")
        business_id = task.get("business_id")
        payload = task.get("payload", {})
        task_title = task.get("title") or payload.get("prompt", task_type)[:80]

    conv_id = payload.get("conversation_id")
    logger.info(f"Processing task [#{task_id}] title=[{task_title}] type=[{task_type}] agent=[{agent_name}]")

    try:
        r_live = get_redis_client()
    except Exception:
        r_live = None

    if r_live:
        _set_worker_state(r_live, {
            "status": "working",
            "task_id": task_id,
            "title": task_title,
            "agent_name": agent_name,
            "step": f"1/4 Carregando memória operacional de {agent_name} e validando Gatekeeper...",
            "progress_percent": 20,
            "started_at": datetime.utcnow().isoformat()
        })

    # --- 1. Load Agent Persona, Memories & Real Spend from DB ---
    db_ctx = _load_agent_context_from_db(agent_name, business_id)
    payload["current_month_spent_brl"] = db_ctx["current_month_spent_brl"]

    # --- 2. Gatekeeper Validation ---
    gatekeeper = Gatekeeper(monthly_budget_limit=MONTHLY_BUDGET_LIMIT)
    try:
        approved, reason = gatekeeper.validate_action(agent_name, task_type, payload)
    except GatekeeperViolation as e:
        logger.error(f"Task [#{task_id}] BLOCKED by Gatekeeper — FORBIDDEN COMMAND: {e}")
        if r_live:
            _publish_task_result(r_live, task_id, {
                "task_id": task_id,
                "status": "blocked",
                "reason": f"Gatekeeper: comando proibido detectado — {e}",
            })
        _update_db_task_status(task_id, "failed", {"status": "blocked"}, str(e), conv_id, agent_name)
        return

    if not approved:
        logger.warning(f"Task [#{task_id}] requires approval / blocked by Gatekeeper: {reason}")
        _create_approval_request_in_db(agent_name, task_type, reason, task_id, business_id, payload)
        if r_live:
            _publish_task_result(r_live, task_id, {
                "task_id": task_id,
                "status": "pending_approval",
                "reason": reason,
            })
        _update_db_task_status(task_id, "failed", {"status": "pending_approval"}, reason, conv_id, agent_name)
        return

    prompt = payload.get("prompt") or task_title
    if not prompt:
        logger.warning(f"Task [#{task_id}] has no prompt. Failing.")
        _update_db_task_status(task_id, "failed", {}, "Tarefa sem prompt definido.", conv_id, agent_name)
        return

    # --- 3. Real-Time Web Search & Context Gathering ---
    web_context_block = ""
    search_results: List[Dict[str, str]] = []
    if _should_perform_web_search(task_type, agent_name, prompt):
        if r_live:
            _set_worker_state(r_live, {
                "status": "working",
                "task_id": task_id,
                "title": task_title,
                "agent_name": agent_name,
                "step": f"2/4 {agent_name} pesquisando dados, preços e fontes reais na internet...",
                "progress_percent": 45,
                "started_at": datetime.utcnow().isoformat()
            })
        clean_search_q = _clean_search_query(prompt)
        logger.info(f"Task [#{task_id}] executing live web research for query: '{clean_search_q}'")
        search_results = _web_search_live(clean_search_q, max_results=12)

        # If query mentions TikTok Shop specifically, also run a targeted secondary search
        if "tiktok" in prompt.lower() and len(search_results) < 8:
            extra = _web_search_live("produtos mais vendidos virais TikTok Shop Brasil tendencia", max_results=8)
            existing_urls = {x["url"] for x in search_results}
            for ex in extra:
                if ex["url"] not in existing_urls:
                    search_results.append(ex)
                    existing_urls.add(ex["url"])

        if search_results:
            lines = ["<live_web_research_results>"]
            for idx, item in enumerate(search_results[:12], 1):
                lines.append(f"  {idx}. {item['title']} — {item['snippet']} (URL Real Verificada: {item['url']})")
            lines.append("</live_web_research_results>")
            web_context_block = "\n".join(lines)

    # --- 4. Build Agent System Prompt & Enriched User Prompt ---
    base_persona = db_ctx["agent_system_prompt"] or (
        f"Você é {agent_name} ({db_ctx['agent_role']}), agente autônomo de segundo plano do SpirandeliEmpire OS."
    )
    system_prompt = payload.get("system_prompt") or (
        f"{base_persona}\n"
        f"Orçamento atual do Império: R$ {db_ctx['current_month_spent_brl']:.2f} / R$ {MONTHLY_BUDGET_LIMIT:.2f}.\n"
        f"{db_ctx['business_info']}\n"
        f"{db_ctx['memories_block']}\n"
        "DIRETRIZ DE EXECUÇÃO E PROIBIÇÃO DE ALUCINAÇÃO:\n"
        "1. Você está executando uma tarefa real em segundo plano com acesso aos resultados reais da internet em <live_web_research_results>.\n"
        "2. PROIBIDO INVENTAR LINKS FALSOS: JAMAIS invente URLs fictícias como 'https://www.tiktokshop.com.br/...' (esse formato de link não existe!). "
        "Use EXCLUSIVAMENTE as URLs reais fornecidas dentro de <live_web_research_results> ou links reais de busca no formato https://www.tiktok.com/search?q=Termo.\n"
        "3. Baseie sua lista de produtos, preços e tendências nos itens reais retornados em <live_web_research_results>, citando as fontes reais verificadas.\n"
        "4. Entregue o trabalho COMPLETO em Markdown com plano de ação prático, ganchos de vídeo virais e links reais."
    )

    enriched_prompt = prompt
    if web_context_block:
        enriched_prompt = (
            f"SOLICITAÇÃO DO COMANDANTE:\n{prompt}\n\n"
            f"DADOS REAIS COLETADOS NA INTERNET AGORA PELO AGENTE ({len(search_results)} fontes verificadas):\n{web_context_block}\n\n"
            "REGRAS OBRIGATÓRIAS PARA ESTA ENTREGA:\n"
            "- Utilize os produtos, preços e informações REAIS listados acima em <live_web_research_results>.\n"
            "- NÃO INVENTE links falsos (nunca escreva tiktokshop.com.br/nome-do-produto). Copie exatamente as 'URL Real Verificada' presentes nos dados acima.\n"
            "- Elabore a entrega completa, detalhada e acionável em português brasileiro:"
        )

    # If this task waited on a parent task in a chained pipeline, inject the parent task's full output
    parent_output = payload.get("parent_task_output")
    if parent_output:
        p_id = payload.get("parent_task_id", "?")
        p_title = payload.get("parent_task_title", f"Tarefa #{p_id}")
        enriched_prompt = (
            f"=== RESULTADO ENTREGUE PELA TAREFA ANTERIOR (#{p_id} — {p_title}) ===\n"
            f"{parent_output}\n"
            f"========================================================================\n\n"
            f"MISSÃO DESTA ETAPA ENCADEDA (USE EXCLUSIVAMENTE OS DADOS/PRODUTOS DA TAREFA ANTERIOR ACIMA):\n"
            f"{enriched_prompt}"
        )

    # --- 5. Execute AI Inference (or Specialized Video Pipeline) ---
    provider = payload.get("provider")
    if task_type == "tiktok_video_pipeline":
        if r_live:
            _set_worker_state(r_live, {
                "status": "working",
                "task_id": task_id,
                "title": task_title,
                "agent_name": agent_name,
                "step": "3/4 Executando pipeline TikTok Shop (Roteiro + Voz + Render Anti-Ban)...",
                "progress_percent": 70,
                "started_at": datetime.utcnow().isoformat()
            })
        try:
            sys.path.insert(0, "/app/ai-engine/workers")
            from tiktok_shop_worker import run_pipeline
            product_info = {
                "name": payload.get("product_name") or task_title,
                "price": payload.get("product_price") or "Oferta Especial",
                "category": payload.get("category") or "generic",
            }
            pipe_res = run_pipeline(product_info)
            if pipe_res.get("output_video") or pipe_res.get("script"):
                ai_result = {
                    "success": True,
                    "response": (
                        f"🎬 **Pipeline TikTok Shop Executado**\n"
                        f"- **Produto:** {pipe_res.get('product')}\n"
                        f"- **Status:** `{pipe_res.get('status')}`\n"
                        f"- **Vídeo Renderizado:** `{pipe_res.get('output_video') or 'Aguardando B-roll na pasta content/broll'}`\n\n"
                        f"### Roteiro Gerado:\n{pipe_res.get('script', '')}"
                    ),
                    "provider": "tiktok_pipeline",
                    "model": _resolve_ollama_model(),
                    "latency_ms": 0,
                }
            else:
                ai_result = query_ai_engine(enriched_prompt, system_prompt, provider)
        except Exception as e:
            logger.warning(f"TikTok video pipeline fallback to standard AI engine: {e}")
            ai_result = query_ai_engine(enriched_prompt, system_prompt, provider)
    else:
        if r_live:
            _set_worker_state(r_live, {
                "status": "working",
                "task_id": task_id,
                "title": task_title,
                "agent_name": agent_name,
                "step": f"3/4 Sintetizando entrega completa com {agent_name} no motor de IA ({provider or 'híbrido'})...",
                "progress_percent": 75,
                "started_at": datetime.utcnow().isoformat()
            })

        task_role = _classify_task_role(prompt, task_type)
        allow_gemini = bool(payload.get("allow_gemini", True))
        avail_cfg = _get_ai_availability_config()
        enabled_provs = avail_cfg.get("enabled_providers", {})
        g_key, o_key = _get_active_api_keys()
        has_gemini_allowed = len(g_key) > 10 and bool(enabled_provs.get("gemini", True)) and allow_gemini
        has_openai_allowed = len(o_key) > 10 and bool(enabled_provs.get("openai", True))
        cloud_executor_ready = (has_gemini_allowed or has_openai_allowed) and provider not in ("ollama", "llama")

        llama_analysis_block = ""
        llama_analyzer_model = None
        if cloud_executor_ready and task_role == "execute_task":
            raw_for_llama = "\n".join(filter(None, [db_ctx.get("business_info", ""), web_context_block]))
            if raw_for_llama.strip():
                if r_live:
                    _set_worker_state(r_live, {
                        "status": "working",
                        "task_id": task_id,
                        "title": task_title,
                        "agent_name": agent_name,
                        "step": f"2.5/4 [Llama Local] Lendo e analisando dados brutos para preparar execução...",
                        "progress_percent": 62,
                        "started_at": datetime.utcnow().isoformat()
                    })
                logger.info(f"Task [#{task_id}] Stage 1: Llama Local reading and analyzing context...")
                llama_res = _llama_read_and_analyze(raw_for_llama, prompt)
                if llama_res and llama_res.get("success") and llama_res.get("response"):
                    llama_analysis_block = llama_res["response"].strip()
                    llama_analyzer_model = llama_res.get("model", _resolve_ollama_model())
                    enriched_prompt = (
                        f"{enriched_prompt}\n\n"
                        f"### ANÁLISE PRÉVIA REALIZADA PELO LLAMA LOCAL ({llama_analyzer_model}):\n"
                        f"{llama_analysis_block}\n\n"
                        "Agora EXECUTE a tarefa final de forma completa usando exclusivamente os links e fatos reais acima:"
                    )

            if r_live:
                exec_name = "Google Gemini" if has_gemini_allowed else "OpenAI ChatGPT"
                _set_worker_state(r_live, {
                    "status": "working",
                    "task_id": task_id,
                    "title": task_title,
                    "agent_name": agent_name,
                    "step": f"3/4 [{exec_name}] Executando a tarefa final com {agent_name}...",
                    "progress_percent": 80,
                    "started_at": datetime.utcnow().isoformat()
                })

        logger.info(f"Task [#{task_id}] querying AI engine (provider={provider or 'auto'}, role={task_role}, allow_gemini={allow_gemini})...")
        ai_result = query_ai_engine(enriched_prompt, system_prompt, provider, task_role, allow_gemini=allow_gemini)

        # Post-processing anti-hallucination guard: replace any invented tiktokshop.com.br/slug URLs with real TikTok search URLs
        if ai_result.get("success") and ai_result.get("response"):
            resp_txt = ai_result["response"]
            resp_txt = re.sub(
                r"https?://(?:www\.)?tiktokshop\.com(?:\.br)?/([a-zA-Z0-9_\-/]+)",
                lambda m: f"https://www.tiktok.com/search?q={urllib.parse.quote(m.group(1).replace('-', ' ').replace('/', ' ').strip())}",
                resp_txt
            )
            if search_results and "Fontes Reais Consultadas" not in resp_txt:
                sources_md = ["\n\n---\n### 🌐 Fontes e Links Reais Consultados em Tempo Real:"]
                for idx, s_item in enumerate(search_results[:10], 1):
                    sources_md.append(f"{idx}. **[{s_item['title']}]({s_item['url']})** — _{s_item['snippet'][:160]}_")
                resp_txt += "\n".join(sources_md)
            ai_result["response"] = resp_txt

        if llama_analysis_block and ai_result.get("success") and ai_result.get("response"):
            exec_label = "Google Gemini" if ai_result.get("provider") == "google_gemini" else (
                "OpenAI ChatGPT" if ai_result.get("provider") == "openai" else ai_result.get("provider", "IA")
            )
            header_badge = (
                f"> 🦙 **Leitura & Análise Prévia:** Llama Local (`{llama_analyzer_model}`) • "
                f"✨ **Execução da Tarefa:** {exec_label} (`{ai_result.get('model')}`) • "
                f"🌐 **Fontes Web Reais:** {len(search_results)}\n\n"
            )
            ai_result["response"] = header_badge + ai_result["response"]
            ai_result["analyzer_model"] = llama_analyzer_model

    # --- 6. Save Deliverable & Publish Result ---
    if r_live:
        _set_worker_state(r_live, {
            "status": "working",
            "task_id": task_id,
            "title": task_title,
            "agent_name": agent_name,
            "step": "4/4 Salvando arquivo de entrega e publicando resultado no chat...",
            "progress_percent": 95,
            "started_at": datetime.utcnow().isoformat()
        })

    saved_file = None
    if ai_result.get("success") and ai_result.get("response"):
        saved_file = _save_task_deliverable(
            task_id,
            task_title,
            ai_result["response"],
            db_ctx.get("business_slug")
        )

    result_payload = {
        "task_id": task_id,
        "task_type": task_type,
        "status": "completed" if ai_result.get("success") else "failed",
        "response": ai_result.get("response", ""),
        "provider": ai_result.get("provider"),
        "model": ai_result.get("model"),
        "latency_ms": ai_result.get("latency_ms", 0),
        "fallback_used": ai_result.get("fallback_used", False),
        "estimated_tokens": ai_result.get("estimated_tokens", 0),
        "web_sources_count": len(search_results),
        "saved_file": saved_file,
        "error": ai_result.get("error") if not ai_result.get("success") else None,
        "completed_at": datetime.utcnow().isoformat(),
    }

    try:
        r_client = get_redis_client()
        _publish_task_result(r_client, task_id, result_payload)
        _update_db_task_status(
            task_id,
            result_payload["status"],
            result_payload,
            result_payload["error"],
            conv_id,
            agent_name
        )
        _record_agent_decision(
            agent_name,
            business_id,
            f"background_task_{task_type}",
            f"Tarefa #{task_id} ({task_title[:60]}) finalizada com status [{result_payload['status']}]",
            {
                "task_id": task_id,
                "provider": result_payload["provider"],
                "model": result_payload["model"],
                "latency_ms": result_payload["latency_ms"],
                "web_sources": len(search_results),
            }
        )
        _set_worker_state(r_client, {
            "status": "idle",
            "step": f"Última entrega (#{task_id} — {agent_name}) concluída com sucesso.",
            "progress_percent": 100,
            "updated_at": datetime.utcnow().isoformat()
        })
        logger.info(
            f"Task [#{task_id}] completed! Status={result_payload['status']} | Provider={ai_result.get('provider')} "
            f"| Model={ai_result.get('model')} | WebSources={len(search_results)} | Latency={ai_result.get('latency_ms', 0)}ms"
        )
    except Exception as e:
        logger.error(f"Task [#{task_id}] failed to publish final result: {e}")

    # --- 7. Immediately trigger any dependent child tasks waiting on this task_id ---
    if result_payload["status"] == "completed" and str(task_id).isdigit():
        try:
            conn = get_db_connection()
            dep_tasks: List[Dict[str, Any]] = []
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, type, agent_name, business_id, payload
                    FROM tasks
                    WHERE status = 'pending'
                      AND payload->>'depends_on_task_id' = %s
                    ORDER BY id ASC
                    """,
                    (str(task_id),)
                )
                dep_rows = cur.fetchall()
                for dr in dep_rows:
                    raw_p = dr[5]
                    p_dict = raw_p if isinstance(raw_p, dict) else (json.loads(raw_p) if raw_p else {})
                    dep_tasks.append({
                        "id": str(dr[0]),
                        "title": dr[1],
                        "type": dr[2] or "content_creation",
                        "agent_name": dr[3] or "Copy & Hooks Agent",
                        "business_id": dr[4],
                        "payload": p_dict,
                    })
            conn.close()
            for dep_t in dep_tasks:
                logger.info(f"Chained Pipeline: Unlocking dependent Task #{dep_t['id']} ({dep_t['title']}) after completion of Task #{task_id}!")
                process_task(dep_t)
        except Exception as e:
            logger.warning(f"Dependent task check warning after task #{task_id}: {e}")


def _check_scheduled_business_automations() -> List[Dict[str, Any]]:
    """
    Check active businesses with auto_enabled=True in settings->automation_params.
    If their scheduled interval has elapsed and no pending/in_progress task is running for that business,
    create a scheduled business automation task in PostgreSQL and return it for immediate execution.
    """
    scheduled_tasks: List[Dict[str, Any]] = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, slug, category, settings FROM businesses WHERE status = 'active'")
            rows = cur.fetchall()
            now_dt = datetime.utcnow()

            for row in rows:
                b_id, b_name, b_slug, b_cat, raw_settings = row
                settings = raw_settings if isinstance(raw_settings, dict) else (json.loads(raw_settings) if raw_settings else {})
                params = settings.get("automation_params") or {}
                accounts = settings.get("accounts") or []

                if not isinstance(params, dict) or not params.get("auto_enabled", False):
                    continue

                freq = params.get("frequency", "daily")
                interval_hours = 24
                if freq == "every_6h":
                    interval_hours = 6
                elif freq == "every_12h":
                    interval_hours = 12
                elif freq == "weekly":
                    interval_hours = 168

                last_run_str = params.get("last_auto_run_at")
                should_run = False
                if not last_run_str:
                    # Wait until first manual trigger or 1 hour after startup if never run
                    continue
                else:
                    try:
                        clean_iso = str(last_run_str).replace("Z", "+00:00")
                        last_dt = datetime.fromisoformat(clean_iso).replace(tzinfo=None)
                        elapsed_hours = (now_dt - last_dt).total_seconds() / 3600.0
                        if elapsed_hours >= interval_hours:
                            should_run = True
                    except Exception:
                        should_run = False

                if not should_run:
                    continue

                # Check if business already has a pending or in_progress task
                cur.execute(
                    "SELECT COUNT(*) FROM tasks WHERE business_id = %s AND status IN ('pending', 'in_progress')",
                    (b_id,)
                )
                active_count = cur.fetchone()[0]
                if active_count > 0:
                    continue

                agent_name = params.get("assigned_agent", "Jeffrey")
                goal = params.get("daily_deliverables_goal", 3)
                niche = params.get("niche", b_cat)
                title = f"Ciclo Agendado [{b_name}]: {goal} entregáveis ({niche})"

                acc_summary = "\n".join([
                    f"- {a.get('platform', 'Conta')}: {a.get('handle', '')} (ID: {a.get('account_id', '')}, Link: {a.get('affiliate_showcase_url', '')})"
                    for a in accounts if isinstance(a, dict)
                ]) or "- Nenhuma conta cadastrada."

                prompt_text = (
                    f"Execute o ciclo periódico automatizado do negócio **{b_name}** ({b_cat}).\n\n"
                    f"### CONTAS DO NEGÓCIO:\n{acc_summary}\n\n"
                    f"### PARÂMETROS DO AGENTE:\n"
                    f"- Nicho: {niche}\n"
                    f"- Público-Alvo: {params.get('target_audience', '')}\n"
                    f"- Meta: {goal} entregáveis completos\n"
                    f"- Comissão Mínima: {params.get('min_commission_percent', 15)}% | Faixa: R$ {params.get('price_range_brl', '29-197')}\n"
                    f"- Tom de Voz: {params.get('tone_of_voice', 'Persuasivo')}\n"
                    f"- CTA Padrão: {params.get('cta_template', '')}\n"
                    f"- Regras: {params.get('custom_prompt_rules', '')}\n"
                )

                task_payload = {
                    "prompt": prompt_text,
                    "business_slug": b_slug,
                    "business_name": b_name,
                    "accounts": accounts,
                    "automation_params": params,
                    "scheduled_cycle": True,
                }

                cur.execute(
                    """
                    INSERT INTO tasks (business_id, title, type, agent_name, payload, status, created_at, updated_at)
                    VALUES (%s, %s, 'business_automation', %s, %s, 'pending', NOW(), NOW())
                    RETURNING id
                    """,
                    (b_id, title[:120], agent_name, json.dumps(task_payload))
                )
                new_task_id = cur.fetchone()[0]

                params["last_auto_run_at"] = now_dt.isoformat()
                settings["automation_params"] = params
                cur.execute(
                    "UPDATE businesses SET settings = %s, updated_at = NOW() WHERE id = %s",
                    (json.dumps(settings), b_id)
                )
                conn.commit()

                scheduled_tasks.append({
                    "id": str(new_task_id),
                    "type": "business_automation",
                    "agent_name": agent_name,
                    "business_id": b_id,
                    "title": title[:120],
                    "payload": {
                        **task_payload,
                        "task_id": new_task_id,
                    }
                })
        conn.close()
    except Exception as e:
        logger.debug(f"Scheduled business automation check skipped: {e}")

    return scheduled_tasks


def main():
    logger.info("Initializing Jeffrey Orchestrator v3.0 (Autonomous Multi-Agent Worker)...")
    logger.info(f"Budget Hard Cap: R$ {MONTHLY_BUDGET_LIMIT:.2f}/month")
    logger.info(f"AI Strategy: {AI_PROVIDER} | Listening on keys: {QUEUE_KEYS}")

    r = None
    while not r:
        try:
            r = get_redis_client()
            r.ping()
            logger.info("Connected to Redis broker.")
        except Exception:
            logger.info("Waiting for Redis broker to be ready...")
            time.sleep(3)

    test_ai_connections()
    logger.info("Jeffrey Worker is now actively listening for empire tasks (Redis + PostgreSQL Auto-Recovery)...")

    last_db_recovery_check = 0.0
    last_schedule_check = 0.0

    while True:
        try:
            _set_worker_state(r, {
                "status": "idle",
                "step": "Ocioso — Aguardando novas ordens ou tarefas assíncronas.",
                "progress_percent": 0,
                "updated_at": datetime.utcnow().isoformat()
            })

            # Listen to both unprefixed and legacy-prefixed Redis queues simultaneously
            task_raw = r.brpop(QUEUE_KEYS, timeout=6)
            if task_raw:
                queue_name, task_data = task_raw
                task = json.loads(task_data)
                logger.info(f"Dequeued task from [{queue_name}]: #{task.get('id', 'unknown')} | Type: {task.get('type')}")
                process_task(task)
                continue

            # Periodic PostgreSQL orphan task recovery (every 10 seconds when idle)
            now_ts = time.time()
            if (now_ts - last_db_recovery_check) >= 10.0:
                last_db_recovery_check = now_ts
                orphan_tasks = _recover_orphan_db_tasks()
                for orphan in orphan_tasks:
                    logger.info(f"Auto-recovering orphan PostgreSQL task #{orphan['id']}: {orphan['title']}")
                    process_task(orphan)

            # Periodic autonomous business automation check (every 60 seconds when idle)
            if (now_ts - last_schedule_check) >= 60.0:
                last_schedule_check = now_ts
                auto_tasks = _check_scheduled_business_automations()
                for auto_task in auto_tasks:
                    logger.info(f"Running scheduled business automation task #{auto_task['id']}: {auto_task['title']}")
                    process_task(auto_task)

        except redis.ConnectionError as e:
            logger.error(f"Redis connection lost in Jeffrey worker: {e}. Reconnecting in 5s...")
            time.sleep(5)
            r = None
            while not r:
                try:
                    r = get_redis_client()
                    r.ping()
                    logger.info("Reconnected to Redis broker successfully.")
                except Exception:
                    time.sleep(3)
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted task JSON payload discarded: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in main worker loop: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
