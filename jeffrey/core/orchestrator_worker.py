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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

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
    """Inspect installed Ollama models and pick an available one to prevent 404 errors."""
    target = requested_model or LLAMA_MODEL
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=4.0)
        if r.status_code == 200:
            models = r.json().get("models", [])
            installed = [m.get("name") for m in models if m.get("name")]
            if not installed:
                return target
            if target in installed:
                return target
            for preferred in ("qwen2.5:3b", "llama3.2:3b", "llama3.2:1b", "qwen2.5:1.5b"):
                if preferred in installed:
                    return preferred
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


def query_gemini(prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not GEMINI_API_KEY:
        return None
    try:
        url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        start = time.time()
        res = httpx.post(url, json=payload, timeout=45.0)
        latency = int((time.time() - start) * 1000)

        if res.status_code == 200:
            data = res.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {
                "success": True,
                "response": text,
                "provider": "google_gemini",
                "model": GEMINI_MODEL,
                "latency_ms": latency
            }
        logger.warning(f"Gemini API returned error {res.status_code}: {res.text[:200]}")
    except Exception as e:
        logger.error(f"Gemini execution failed: {e}")
    return None


def query_openai(prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not OPENAI_API_KEY:
        return None
    try:
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
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


def determine_optimal_provider(estimated_tokens: int, requested_provider: Optional[str] = None) -> Tuple[str, str]:
    if requested_provider and requested_provider not in ("hybrid", "auto"):
        if requested_provider in ("ollama", "llama") and estimated_tokens > 6000 and GEMINI_API_KEY:
            return "gemini", f"Contexto de {estimated_tokens} tokens excede janela segura do Llama local. Delegado ao Gemini."
        return requested_provider, f"Provedor {requested_provider} requisitado explicitamente."

    if GEMINI_API_KEY:
        if estimated_tokens <= 800 and not GEMINI_API_KEY:
            return "ollama", f"Tarefa leve (~{estimated_tokens} tokens). Resolvida localmente no Ollama."
        return "gemini", f"Tarefa de agente (~{estimated_tokens} tokens). Delegada ao Google Gemini Free Tier para máxima velocidade e inteligência."

    if OPENAI_API_KEY:
        return "openai", f"Tarefa de agente (~{estimated_tokens} tokens). Delegada ao OpenAI."

    return "ollama", f"Provedores cloud não configurados; executando localmente no Ollama (~{estimated_tokens} tokens)."


def query_ai_engine(prompt: str, system_prompt: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """Execute AI inference with smart provider routing and full fallback chain."""
    full_text = prompt + (" " + system_prompt if system_prompt else "")
    est_tokens = estimate_tokens(full_text)
    optimal_prov, delegation_reason = determine_optimal_provider(est_tokens, provider)

    logger.info(f"Token analysis: ~{est_tokens} tokens | Routing: [{optimal_prov}] | {delegation_reason}")
    prov = optimal_prov

    if prov == "gemini":
        res = query_gemini(prompt, system_prompt)
        if res:
            res["estimated_tokens"] = est_tokens
            res["delegation_reason"] = delegation_reason
            return res
        logger.warning("Gemini unavailable, falling back to OpenAI / Ollama...")
        if OPENAI_API_KEY:
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
        if GEMINI_API_KEY:
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
        if GEMINI_API_KEY:
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

def _web_search_live(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """Perform zero-cost live web search via DuckDuckGo HTML & Google News RSS fallback."""
    results: List[Dict[str, str]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    # 1. Try DuckDuckGo HTML Search
    try:
        resp = httpx.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "kl": "br-pt"},
            headers=headers,
            timeout=10.0,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            body = resp.text
            # Match result blocks
            titles = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body, re.S)
            snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', body, re.S)
            for idx, (href, raw_title) in enumerate(titles[:max_results]):
                clean_title = re.sub(r"<[^>]+>", "", html.unescape(raw_title)).strip()
                clean_snip = ""
                if idx < len(snippets):
                    clean_snip = re.sub(r"<[^>]+>", "", html.unescape(snippets[idx])).strip()
                if clean_title:
                    results.append({
                        "title": clean_title,
                        "url": href,
                        "snippet": clean_snip,
                    })
    except Exception as e:
        logger.warning(f"DuckDuckGo search warning: {e}")

    # 2. Fallback / Supplement with Google News RSS (PT-BR)
    if len(results) < 3:
        try:
            encoded_q = urllib.parse.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            resp = httpx.get(rss_url, headers=headers, timeout=8.0, follow_redirects=True)
            if resp.status_code == 200:
                items = re.findall(r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>.*?</item>", resp.text, re.S)
                for raw_t, link, pub_date in items[:max_results]:
                    clean_t = html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", raw_t)).strip()
                    results.append({
                        "title": clean_t,
                        "url": link.strip(),
                        "snippet": f"Publicado em {pub_date.strip()}",
                    })
        except Exception as e:
            logger.warning(f"Google News RSS search warning: {e}")

    return results[:max_results]


def _should_perform_web_search(task_type: str, agent_name: str, prompt: str) -> bool:
    """Detect if the task requires real-time web / market / product research."""
    combined = f"{task_type} {agent_name} {prompt}".lower()
    keywords = [
        "pesquis", "research", "tiktok", "produto", "viral", "tendência", "tendencia",
        "mercado", "nicho", "concorr", "amazon", "kdp", "youtube", "shorts", "busca",
        "identificar", "levantamento", "top 10", "top 5", "afiliado", "preço", "preco",
        "históri", "histori", "bíbli", "bibli", "referência", "referencia"
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

            # 3. Business context (or list of businesses)
            if business_id and str(business_id).isdigit():
                cur.execute(
                    "SELECT name, slug, category, description, budget_limit_brl FROM businesses WHERE id = %s",
                    (int(business_id),)
                )
                b_row = cur.fetchone()
                if b_row:
                    ctx["business_slug"] = b_row[1]
                    ctx["business_info"] = f"Negócio em foco: {b_row[0]} ({b_row[2]}) — {b_row[3]} | Teto: R$ {b_row[4]}"
            else:
                cur.execute("SELECT name, slug, category, status FROM businesses WHERE status = 'active' LIMIT 6")
                b_rows = cur.fetchall()
                if b_rows:
                    b_summary = ", ".join([f"{r[0]} ({r[2]})" for r in b_rows])
                    ctx["business_info"] = f"Negócios ativos no Império: {b_summary}"

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
    Check if task exists in PostgreSQL and is eligible to run (not already cancelled or completed).
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

            cur.execute("""
                UPDATE tasks
                SET status = 'in_progress', started_at = NOW(), error_message = NULL, updated_at = NOW()
                WHERE id = %s
            """, (int(task_id),))
            conn.commit()

            payload_val = row[6] if isinstance(row[6], dict) else (json.loads(row[6]) if row[6] else {})
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
                "step": f"2/4 {agent_name} pesquisando dados e tendências em tempo real na web...",
                "progress_percent": 45,
                "started_at": datetime.utcnow().isoformat()
            })
        search_query = re.sub(r"^(execute de forma completa.*?:)\s*", "", prompt, flags=re.I | re.S).strip()
        search_query = search_query[:140]
        logger.info(f"Task [#{task_id}] executing live web research for query: '{search_query}'")
        search_results = _web_search_live(search_query, max_results=8)

        # If query mentions TikTok Shop specifically, also run a targeted secondary search
        if "tiktok" in search_query.lower() and len(search_results) < 5:
            extra = _web_search_live("TikTok Shop produtos mais vendidos virais Brasil 2025 2026", max_results=6)
            search_results.extend(extra)

        if search_results:
            lines = ["<live_web_research_results>"]
            for idx, item in enumerate(search_results[:10], 1):
                lines.append(f"  {idx}. {item['title']} — {item['snippet']} (Fonte: {item['url']})")
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
        "DIRETRIZ DE EXECUÇÃO: Você está executando uma tarefa real em segundo plano. "
        "Entregue o trabalho COMPLETO, estruturado em Markdown, com dados concretos, plano de ação prático, "
        "exemplos de ganchos/roteiros ou análises detalhadas prontas para uso imediato pelo Comandante. "
        "Jamais responda que 'vai pesquisar depois' — você É o worker final de execução!"
    )

    enriched_prompt = prompt
    if web_context_block:
        enriched_prompt = (
            f"SOLICITAÇÃO DO COMANDANTE:\n{prompt}\n\n"
            f"DADOS COLETADOS NA WEB EM TEMPO REAL PELO AGENTE:\n{web_context_block}\n\n"
            "Com base nos dados coletados e na sua especialidade, elabore a entrega completa, detalhada e acionável em português brasileiro:"
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

        logger.info(f"Task [#{task_id}] querying AI engine (provider={provider or 'auto'})...")
        ai_result = query_ai_engine(enriched_prompt, system_prompt, provider)

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
