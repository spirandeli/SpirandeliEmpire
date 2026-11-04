"""
SpirandeliEmpire OS - Jeffrey Orchestrator Daemon Worker
Central task processing & multi-provider AI coordinator (Google Gemini, OpenAI, Llama)
"""
import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
import redis

# Importa o Gatekeeper de segurança/governança
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from permissions.gatekeeper import Gatekeeper, GatekeeperViolation

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
# 1. Google Gemini (Free tier from Google AI Studio / Paid credits)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

# 2. OpenAI (Credits / Plans)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# 3. Local Llama via Ollama (100% Free & Offline)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", os.getenv("DEFAULT_TEXT_MODEL", "llama3.2:3b"))

def get_redis_client():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD if REDIS_PASSWORD else None,
        decode_responses=True
    )

def test_ai_connections():
    """Verify connectivity to all configured AI providers."""
    # Test Google Gemini
    if GEMINI_API_KEY:
        try:
            url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"role": "user", "parts": [{"text": "ping"}]}]}
            res = httpx.post(url, json=payload, timeout=8.0)
            if res.status_code == 200:
                logger.info(f"Google Gemini connected successfully. Model: {GEMINI_MODEL} (Free Tier Eligible)")
            else:
                logger.warning(f"Google Gemini returned HTTP {res.status_code}: {res.text[:100]}")
        except Exception as e:
            logger.warning(f"Google Gemini connection check failed: {e}")
    else:
        logger.info("Google Gemini key not configured (GEMINI_API_KEY empty). Set it to use free AI Studio credits.")

    # Test OpenAI
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

    # Test Ollama Local Llama
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if r.status_code == 200:
            models = r.json().get("models", [])
            model_names = [m.get("name") for m in models]
            logger.info(f"Local Ollama AI service connected successfully. Installed: {model_names} | Target: {LLAMA_MODEL}")
            return True
    except Exception as e:
        logger.warning(f"Ollama connection check pending: {e}")
    return False

def query_gemini(prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not GEMINI_API_KEY:
        return None
    try:
        url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
        
        start = time.time()
        res = httpx.post(url, json=payload, timeout=40.0)
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
        logger.warning(f"Gemini API returned error {res.status_code}")
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
        res = httpx.post(url, headers=headers, json=payload, timeout=40.0)
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
        logger.warning(f"OpenAI API returned error {res.status_code}")
    except Exception as e:
        logger.error(f"OpenAI execution failed: {e}")
    return None

def query_ollama(prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": LLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        start = time.time()
        res = httpx.post(url, json=payload, timeout=90.0)
        latency = int((time.time() - start) * 1000)
        
        if res.status_code == 200:
            return {
                "success": True,
                "response": res.json().get("response", ""),
                "provider": "ollama_llama",
                "model": LLAMA_MODEL,
                "latency_ms": latency
            }
    except Exception as e:
        logger.error(f"Ollama local execution failed: {e}")
    return None

def estimate_tokens(text: str) -> int:
    """Estimate token count for Portuguese / multilingual text (approx 3.6 chars/token)."""
    if not text:
        return 0
    return max(1, int(len(text.strip()) / 3.6))

def determine_optimal_provider(estimated_tokens: int, requested_provider: Optional[str] = None) -> tuple[str, str]:
    """Delimit tasks based on token volume to balance API quotas vs VPS hardware."""
    if requested_provider and requested_provider not in ("hybrid", "auto"):
        if requested_provider in ("ollama", "llama") and estimated_tokens > 6000:
            return "gemini", f"Contexto de {estimated_tokens} tokens excede janela segura do Llama local na VPS 8GB. Delegado ao Gemini (janela 1M)."
        return requested_provider, f"Provedor {requested_provider} requisitado explicitamente."

    # Tier 1: Micro / Tarefas rápidas (< 800 tokens) -> Llama Local (Poupa cotas de API)
    if estimated_tokens <= 800:
        return "ollama", f"Tarefa leve (~{estimated_tokens} tokens). Resolvida localmente no Llama para economizar créditos de API."

    # Tier 2: Médio porte (800 - 3500 tokens) -> Google Gemini Free Tier (Alta fluência a R$ 0,00)
    if estimated_tokens <= 3500:
        return "gemini", f"Roteiro/tarefa média (~{estimated_tokens} tokens). Delegada ao Google Gemini Free Tier."

    # Tier 3: Contexto Massivo (> 3500 tokens) -> Google Gemini 1.5 Flash (1M tokens)
    return "gemini", f"Contexto extenso (~{estimated_tokens} tokens). Delegado ao Gemini 1.5 Flash para proteger a RAM da VPS."

def query_ai_engine(prompt: str, system_prompt: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """Execute AI inference with token verification & smart task delegation."""
    full_text = prompt + (" " + system_prompt if system_prompt else "")
    est_tokens = estimate_tokens(full_text)
    optimal_prov, delegation_reason = determine_optimal_provider(est_tokens, provider)

    logger.info(f"Token analysis: ~{est_tokens} tokens | Routing decision: [{optimal_prov}] | Reason: {delegation_reason}")
    prov = optimal_prov

    if prov == "gemini":
        res = query_gemini(prompt, system_prompt)
        if res:
            res["estimated_tokens"] = est_tokens
            res["delegation_reason"] = delegation_reason
            return res
        logger.warning("Gemini failed, falling back to local Llama...")
        ollama_res = query_ollama(prompt, system_prompt)
        if ollama_res:
            ollama_res["fallback_used"] = True
            ollama_res["estimated_tokens"] = est_tokens
            return ollama_res
        return {"success": False, "error": "All AI failed"}

    if prov == "openai":
        res = query_openai(prompt, system_prompt)
        if res:
            res["estimated_tokens"] = est_tokens
            res["delegation_reason"] = delegation_reason
            return res
        logger.warning("OpenAI failed, falling back to local Llama...")
        ollama_res = query_ollama(prompt, system_prompt)
        if ollama_res:
            ollama_res["fallback_used"] = True
            ollama_res["estimated_tokens"] = est_tokens
            return ollama_res
        return {"success": False, "error": "All AI failed"}

    if prov in ("ollama", "llama"):
        res = query_ollama(prompt, system_prompt)
        if res:
            res["estimated_tokens"] = est_tokens
            res["delegation_reason"] = delegation_reason
            return res
        # Fallback to Gemini if Llama local is offline
        if GEMINI_API_KEY:
            logger.warning("Local Llama offline, falling back to Gemini free tier...")
            gemini_res = query_gemini(prompt, system_prompt)
            if gemini_res:
                gemini_res["fallback_used"] = True
                gemini_res["estimated_tokens"] = est_tokens
                return gemini_res
        return {"success": False, "error": "Local Llama failed and no fallback available"}

    # Hybrid Fallback Chain
    res_gemini = query_gemini(prompt, system_prompt)
    if res_gemini:
        res_gemini["estimated_tokens"] = est_tokens
        return res_gemini

    res_openai = query_openai(prompt, system_prompt)
    if res_openai:
        res_openai["estimated_tokens"] = est_tokens
        return res_openai

    res_ollama = query_ollama(prompt, system_prompt)
    if res_ollama:
        res_ollama["fallback_used"] = True
        res_ollama["estimated_tokens"] = est_tokens
        return res_ollama

    return {"success": False, "error": "No AI provider available (Gemini, OpenAI, Llama failed)"}

def main():
    logger.info("Initializing Jeffrey Orchestrator v2.0 (Multi-Provider AI)...")
    logger.info(f"Budget Hard Cap: R$ {MONTHLY_BUDGET_LIMIT:.2f}/month")
    logger.info(f"AI Strategy: {AI_PROVIDER} | Fallback Chain: Gemini -> OpenAI -> Llama")

    # Wait for Redis
    r = None
    while not r:
        try:
            r = get_redis_client()
            r.ping()
            logger.info("Connected to Redis broker.")
        except Exception as e:
            logger.info("Waiting for Redis broker to be ready...")
            time.sleep(3)

    test_ai_connections()
    logger.info("Jeffrey is now actively listening for empire tasks and events...")

    while True:
        try:
            # Pop task from empire queue with timeout
            task_raw = r.brpop("empire:jeffrey:tasks", timeout=10)
            if task_raw:
                _, task_data = task_raw
                task = json.loads(task_data)
                logger.info(f"Received task: {task.get('id', 'unknown')} | Type: {task.get('type')}")
                process_task(task)
        except redis.ConnectionError as e:
            logger.error(f"Conexão com Redis perdida no worker do Jeffrey: {e}. Reconectando em 5 segundos...")
            time.sleep(5)
            r = None
            while not r:
                try:
                    r = get_redis_client()
                    r.ping()
                    logger.info("Reconectado ao broker Redis com sucesso.")
                except Exception:
                    time.sleep(3)
        except json.JSONDecodeError as e:
            logger.error(f"Payload de tarefa corrompido ou JSON inválido recebido: {e}")
        except Exception as e:
            logger.exception(f"Erro inesperado no loop principal de tarefas: {e}")
            time.sleep(2)

def _publish_task_result(r: redis.Redis, task_id: str, result: Dict[str, Any]) -> None:
    """Publish task result back to Redis so the Laravel backend can pick it up."""
    result_key = f"empire:jeffrey:results:{task_id}"
    r.set(result_key, json.dumps(result), ex=3600)  # TTL: 1 hour
    r.publish("empire:jeffrey:results:channel", json.dumps({"task_id": task_id}))


def _update_db_task_status(task_id: str, status: str, result: Dict[str, Any], error: Optional[str] = None) -> None:
    """Update task record directly in PostgreSQL if task_id corresponds to a database record."""
    if not str(task_id).isdigit():
        return
    try:
        import psycopg2
        db_host = os.getenv("DB_HOST", "postgres")
        db_name = os.getenv("DB_DATABASE", "spirandeli_empire")
        db_user = os.getenv("DB_USERNAME", "empire_admin")
        db_pass = os.getenv("DB_PASSWORD", "")

        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_pass,
            connect_timeout=3
        )
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tasks 
                SET status = %s, result = %s, error_message = %s, completed_at = NOW(), updated_at = NOW()
                WHERE id = %s
            """, (status, json.dumps(result), error, int(task_id)))
            conn.commit()
        conn.close()
        logger.info(f"Task #{task_id} status updated to [{status}] in PostgreSQL.")
    except Exception as e:
        logger.warning(f"Could not update task #{task_id} in PostgreSQL: {e}")


def process_task(task: Dict[str, Any]) -> None:
    """Process incoming empire task under strict security policies.

    Flow:
      1. Validate action via Gatekeeper (budget + critical-action approval + command safety)
      2. Build prompt from task payload
      3. Query AI engine with smart provider routing
      4. Publish result back to Redis for the Laravel API to consume
    """
    task_id   = task.get("id", f"task_{int(time.time())}")
    task_type = task.get("type", "unknown")
    payload   = task.get("payload", {})

    logger.info(f"Processing task [{task_id}] type=[{task_type}]")

    # --- 1. Gatekeeper: validate action before executing anything ---
    gatekeeper = Gatekeeper(monthly_budget_limit=MONTHLY_BUDGET_LIMIT)
    try:
        approved, reason = gatekeeper.validate_action("Jeffrey", task_type, payload)
    except GatekeeperViolation as e:
        logger.error(f"Task [{task_id}] BLOCKED by Gatekeeper — FORBIDDEN COMMAND: {e}")
        try:
            r_client = get_redis_client()
            _publish_task_result(r_client, task_id, {
                "task_id": task_id,
                "status": "blocked",
                "reason": f"Gatekeeper: comando proibido detectado — {e}",
            })
        except Exception:
            pass
        return

    if not approved:
        logger.warning(f"Task [{task_id}] BLOCKED by Gatekeeper: {reason}")
        try:
            r_client = get_redis_client()
            _publish_task_result(r_client, task_id, {
                "task_id": task_id,
                "status": "pending_approval",
                "reason": reason,
            })
        except Exception:
            pass
        return

    # --- 2. Build prompt ---
    prompt        = payload.get("prompt", "")
    system_prompt = payload.get("system_prompt")
    provider      = payload.get("provider")

    if not prompt:
        logger.warning(f"Task [{task_id}] has no prompt. Skipping.")
        return

    # --- 3. Execute AI inference ---
    logger.info(f"Task [{task_id}] approved by Gatekeeper. Querying AI engine (provider={provider or 'auto'})...")
    ai_result = query_ai_engine(prompt, system_prompt, provider)

    # --- 4. Publish result ---
    result_payload = {
        "task_id":   task_id,
        "task_type": task_type,
        "status":    "completed" if ai_result.get("success") else "failed",
        "response":  ai_result.get("response", ""),
        "provider":  ai_result.get("provider"),
        "model":     ai_result.get("model"),
        "latency_ms": ai_result.get("latency_ms", 0),
        "fallback_used": ai_result.get("fallback_used", False),
        "estimated_tokens": ai_result.get("estimated_tokens", 0),
        "error":     ai_result.get("error") if not ai_result.get("success") else None,
        "completed_at": datetime.utcnow().isoformat(),
    }

    try:
        r_client = get_redis_client()
        _publish_task_result(r_client, task_id, result_payload)
        _update_db_task_status(task_id, result_payload["status"], result_payload, result_payload["error"])
        logger.info(
            f"Task [{task_id}] completed. Provider={ai_result.get('provider')} "
            f"| Tokens~{ai_result.get('estimated_tokens', 0)} | Latency={ai_result.get('latency_ms', 0)}ms"
        )
    except Exception as e:
        logger.error(f"Task [{task_id}] failed to publish result to Redis: {e}")

if __name__ == "__main__":
    main()
