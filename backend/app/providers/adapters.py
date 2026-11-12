"""SpirandeliEmpire OS 3.2 — Provider Adapters (Google Gemini, OpenAI, Anthropic Claude)"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from pydantic import BaseModel, Field


class CapabilityInfo(BaseModel):
    capability: str
    supported: bool
    source: str  # provider_api, official_docs, technical_validation, unknown


class DiscoveredModel(BaseModel):
    provider: str
    model_id: str
    display_name: str
    description: str = ""
    version: Optional[str] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supported_methods: List[str] = Field(default_factory=list)
    capabilities: List[CapabilityInfo] = Field(default_factory=list)
    lifecycle_status: str = "active"  # active, deprecated, retired, unconfirmed
    raw_metadata: Dict[str, Any] = Field(default_factory=dict)


class ConnectionTestResult(BaseModel):
    success: bool
    status: str  # Connected, Invalid Credential, Permission Denied, Rate Limited, Provider Unavailable, Configuration Required, Connection Error
    latency_ms: int = 0
    models_count: int = 0
    error_code: Optional[str] = None
    message: str = ""


class AdapterGenerationResult(BaseModel):
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    model_id: str
    provider: str
    duration_ms: int = 0


def _classify_http_error(status_code: int, body_text: str) -> Tuple[str, str]:
    detail = ""
    try:
        data = json.loads(body_text)
        if isinstance(data, dict) and "error" in data:
            err = data["error"]
            detail = err.get("message") if isinstance(err, dict) else str(err)
    except Exception:
        pass

    if not detail:
        detail = body_text[:200] if body_text else f"Status HTTP {status_code}"

    if status_code in (400, 401):
        return "Invalid Credential", f"Credencial inválida ou rejeitada ({status_code}): {detail}"
    if status_code == 403:
        return "Permission Denied", f"Permissão negada pelo provedor ({status_code}): {detail}"
    if status_code == 404:
        return "Model Not Found", f"Modelo não encontrado no provedor ({status_code}): {detail}"
    if status_code == 429:
        return "Rate Limited", f"Limite de requisições atingido (429): {detail}"
    if status_code >= 500:
        return "Provider Unavailable", f"Provedor temporariamente indisponível ({status_code}): {detail}"
    return "Connection Error", f"Erro HTTP {status_code}: {detail}"


class GeminiAdapter:
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    async def list_models(self, api_key: str) -> List[DiscoveredModel]:
        models: List[DiscoveredModel] = []
        page_token: Optional[str] = None

        async with httpx.AsyncClient(timeout=20.0) as client:
            for _ in range(20):  # bounded pagination
                params: Dict[str, Any] = {"key": api_key, "pageSize": 100}
                if page_token:
                    params["pageToken"] = page_token
                resp = await client.get(f"{self.BASE_URL}/models", params=params)
                if resp.status_code != 200:
                    st, msg = _classify_http_error(resp.status_code, resp.text)
                    raise RuntimeError(f"{st}: {msg}")
                data = resp.json()
                for m in data.get("models", []):
                    raw_name = m.get("name", "")
                    model_id = raw_name.replace("models/", "", 1)
                    methods = m.get("supportedGenerationMethods", []) or []
                    is_embed = "embedContent" in methods and "generateContent" not in methods
                    supports_chat = "generateContent" in methods

                    caps: List[CapabilityInfo] = []
                    if supports_chat:
                        caps.append(CapabilityInfo(capability="chat", supported=True, source="provider_api"))
                        caps.append(CapabilityInfo(capability="function_calling", supported=True, source="official_docs"))
                        caps.append(CapabilityInfo(capability="tool_use", supported=True, source="official_docs"))
                        caps.append(CapabilityInfo(capability="structured_output", supported=True, source="official_docs"))
                        caps.append(CapabilityInfo(capability="vision", supported=True, source="official_docs"))
                        caps.append(CapabilityInfo(capability="coding", supported=True, source="official_docs"))
                    if is_embed or "embedContent" in methods:
                        caps.append(CapabilityInfo(capability="embeddings", supported=True, source="provider_api"))
                    if "flash" in model_id.lower():
                        caps.append(CapabilityInfo(capability="fast", supported=True, source="official_docs"))
                        caps.append(CapabilityInfo(capability="cost_efficient", supported=True, source="official_docs"))
                    if "pro" in model_id.lower() or "thinking" in model_id.lower():
                        caps.append(CapabilityInfo(capability="reasoning", supported=True, source="official_docs"))
                    if (m.get("inputTokenLimit") or 0) >= 100_000:
                        caps.append(CapabilityInfo(capability="long_context", supported=True, source="provider_api"))

                    models.append(
                        DiscoveredModel(
                            provider="gemini",
                            model_id=model_id,
                            display_name=m.get("displayName") or model_id,
                            description=m.get("description") or "",
                            version=m.get("version"),
                            context_window=m.get("inputTokenLimit"),
                            max_output_tokens=m.get("outputTokenLimit"),
                            supported_methods=methods,
                            capabilities=caps,
                            lifecycle_status="active",
                            raw_metadata={"supportedGenerationMethods": methods},
                        )
                    )
                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        return models

    async def test_connection(self, api_key: str) -> ConnectionTestResult:
        if not api_key:
            return ConnectionTestResult(success=False, status="Configuration Required", message="API Key não informada.")
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{self.BASE_URL}/models", params={"key": api_key, "pageSize": 20})
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                count = len(resp.json().get("models", []))
                return ConnectionTestResult(
                    success=True,
                    status="Connected",
                    latency_ms=latency,
                    models_count=count,
                    message=f"Conectado ao Google Gemini ({count} modelos na primeira página).",
                )
            st, msg = _classify_http_error(resp.status_code, resp.text)
            return ConnectionTestResult(success=False, status=st, latency_ms=latency, error_code=str(resp.status_code), message=msg)
        except Exception as e:
            return ConnectionTestResult(success=False, status="Connection Error", message=str(e))

    async def generate(
        self,
        api_key: str,
        model_id: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.4,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AdapterGenerationResult:
        t0 = time.monotonic()
        contents = []
        if history:
            for h in history[-6:]:
                contents.append({"role": "user", "parts": [{"text": str(h.get("text", ""))[:2000]}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        resp = None
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(
                        f"{self.BASE_URL}/models/{model_id}:generateContent",
                        params={"key": api_key},
                        json=payload,
                    )
                if resp.status_code == 200:
                    break
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_attempts:
                    await asyncio.sleep(attempt * 1.5)
                    continue
                st, msg = _classify_http_error(resp.status_code, resp.text)
                raise RuntimeError(f"Gemini {st}: {msg}")
            except (httpx.TimeoutException, httpx.RequestError) as net_err:
                if attempt < max_attempts:
                    await asyncio.sleep(attempt * 1.5)
                    continue
                err_detail = str(net_err).strip() or net_err.__class__.__name__
                raise RuntimeError(f"Gemini Connection Error: Falha de rede ou tempo esgotado ({err_detail}).") from net_err

        latency = int((time.monotonic() - t0) * 1000)
        if resp is None or resp.status_code != 200:
            st, msg = _classify_http_error(resp.status_code if resp else 500, resp.text if resp else "")
            raise RuntimeError(f"Gemini {st}: {msg}")

        data = resp.json()
        candidates = data.get("candidates", [])
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
        usage = data.get("usageMetadata", {})
        in_tok = int(usage.get("promptTokenCount", 0))
        out_tok = int(usage.get("candidatesTokenCount", 0))
        cached_tok = int(usage.get("cachedContentTokenCount", 0))
        return AdapterGenerationResult(
            content=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cached_tokens=cached_tok,
            total_tokens=int(usage.get("totalTokenCount", in_tok + out_tok)),
            model_id=model_id,
            provider="gemini",
            duration_ms=latency,
        )


class OpenAIAdapter:
    BASE_URL = "https://api.openai.com/v1"

    def _headers(self, api_key: str, workspace_org: Optional[str] = None) -> Dict[str, str]:
        h = {"Authorization": f"Bearer {api_key}"}
        if workspace_org:
            h["OpenAI-Organization"] = workspace_org
        return h

    def _infer_capabilities(self, model_id: str) -> List[CapabilityInfo]:
        mid = model_id.lower()
        caps: List[CapabilityInfo] = []
        if "embedding" in mid:
            caps.append(CapabilityInfo(capability="embeddings", supported=True, source="official_docs"))
            return caps
        if "whisper" in mid or "transcribe" in mid:
            caps.append(CapabilityInfo(capability="transcription", supported=True, source="official_docs"))
            caps.append(CapabilityInfo(capability="audio", supported=True, source="official_docs"))
            return caps
        if mid.startswith(("gpt-", "o1", "o3", "o4", "chatgpt-")):
            caps.append(CapabilityInfo(capability="chat", supported=True, source="official_docs"))
            caps.append(CapabilityInfo(capability="coding", supported=True, source="official_docs"))
            caps.append(CapabilityInfo(capability="function_calling", supported=True, source="official_docs"))
            caps.append(CapabilityInfo(capability="tool_use", supported=True, source="official_docs"))
            caps.append(CapabilityInfo(capability="structured_output", supported=True, source="official_docs"))
            if "4o" in mid or "4.1" in mid or "gpt-5" in mid:
                caps.append(CapabilityInfo(capability="vision", supported=True, source="official_docs"))
                caps.append(CapabilityInfo(capability="long_context", supported=True, source="official_docs"))
            if mid.startswith(("o1", "o3", "o4")) or "gpt-5" in mid:
                caps.append(CapabilityInfo(capability="reasoning", supported=True, source="official_docs"))
            if "mini" in mid or "nano" in mid:
                caps.append(CapabilityInfo(capability="fast", supported=True, source="official_docs"))
                caps.append(CapabilityInfo(capability="cost_efficient", supported=True, source="official_docs"))
            return caps
        caps.append(CapabilityInfo(capability="chat", supported=False, source="unknown"))
        return caps

    async def list_models(self, api_key: str, workspace_org: Optional[str] = None) -> List[DiscoveredModel]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{self.BASE_URL}/models", headers=self._headers(api_key, workspace_org))
        if resp.status_code != 200:
            st, msg = _classify_http_error(resp.status_code, resp.text)
            raise RuntimeError(f"{st}: {msg}")

        models: List[DiscoveredModel] = []
        for m in resp.json().get("data", []):
            mid = m.get("id", "")
            caps = self._infer_capabilities(mid)
            methods = ["chat.completions"] if any(c.capability == "chat" and c.supported for c in caps) else []
            models.append(
                DiscoveredModel(
                    provider="openai",
                    model_id=mid,
                    display_name=mid,
                    description=f"OpenAI model (owned by {m.get('owned_by', 'openai')})",
                    supported_methods=methods,
                    capabilities=caps,
                    lifecycle_status="active",
                    raw_metadata={"owned_by": m.get("owned_by"), "created": m.get("created")},
                )
            )
        return models

    async def test_connection(self, api_key: str, workspace_org: Optional[str] = None) -> ConnectionTestResult:
        if not api_key:
            return ConnectionTestResult(success=False, status="Configuration Required", message="API Key não informada.")
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{self.BASE_URL}/models", headers=self._headers(api_key, workspace_org))
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                count = len(resp.json().get("data", []))
                return ConnectionTestResult(
                    success=True,
                    status="Connected",
                    latency_ms=latency,
                    models_count=count,
                    message=f"Conectado à OpenAI ({count} modelos disponíveis).",
                )
            st, msg = _classify_http_error(resp.status_code, resp.text)
            return ConnectionTestResult(success=False, status=st, latency_ms=latency, error_code=str(resp.status_code), message=msg)
        except Exception as e:
            return ConnectionTestResult(success=False, status="Connection Error", message=str(e))

    async def generate(
        self,
        api_key: str,
        model_id: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.4,
        history: Optional[List[Dict[str, str]]] = None,
        workspace_org: Optional[str] = None,
    ) -> AdapterGenerationResult:
        t0 = time.monotonic()
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        if history:
            for h in history[-6:]:
                messages.append({"role": "user", "content": str(h.get("text", ""))[:2000]})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self._headers(api_key, workspace_org),
                json={"model": model_id, "messages": messages, "temperature": temperature},
            )
        latency = int((time.monotonic() - t0) * 1000)
        if resp.status_code != 200:
            st, msg = _classify_http_error(resp.status_code, resp.text)
            raise RuntimeError(f"OpenAI {st}: {msg}")

        data = resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        in_tok = int(usage.get("prompt_tokens", 0))
        out_tok = int(usage.get("completion_tokens", 0))
        return AdapterGenerationResult(
            content=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=int(usage.get("total_tokens", in_tok + out_tok)),
            model_id=model_id,
            provider="openai",
            duration_ms=latency,
        )


class AnthropicAdapter:
    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def _headers(self, api_key: str) -> Dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }

    async def list_models(self, api_key: str) -> List[DiscoveredModel]:
        models: List[DiscoveredModel] = []
        after_id: Optional[str] = None

        async with httpx.AsyncClient(timeout=20.0) as client:
            for _ in range(20):
                params: Dict[str, Any] = {"limit": 100}
                if after_id:
                    params["after_id"] = after_id
                resp = await client.get(f"{self.BASE_URL}/models", headers=self._headers(api_key), params=params)
                if resp.status_code != 200:
                    st, msg = _classify_http_error(resp.status_code, resp.text)
                    raise RuntimeError(f"{st}: {msg}")

                data = resp.json()
                for m in data.get("data", []):
                    mid = m.get("id", "")
                    lifecycle = "active"
                    if m.get("retired_at"):
                        lifecycle = "retired"
                    elif m.get("deprecated_at"):
                        lifecycle = "deprecated"

                    caps = [
                        CapabilityInfo(capability="chat", supported=True, source="provider_api"),
                        CapabilityInfo(capability="tool_use", supported=True, source="official_docs"),
                        CapabilityInfo(capability="function_calling", supported=True, source="official_docs"),
                        CapabilityInfo(capability="coding", supported=True, source="official_docs"),
                        CapabilityInfo(capability="vision", supported=True, source="official_docs"),
                        CapabilityInfo(capability="long_context", supported=True, source="official_docs"),
                    ]
                    if "haiku" in mid.lower():
                        caps.append(CapabilityInfo(capability="fast", supported=True, source="official_docs"))
                        caps.append(CapabilityInfo(capability="cost_efficient", supported=True, source="official_docs"))
                    if "opus" in mid.lower() or "sonnet" in mid.lower():
                        caps.append(CapabilityInfo(capability="reasoning", supported=True, source="official_docs"))

                    models.append(
                        DiscoveredModel(
                            provider="anthropic",
                            model_id=mid,
                            display_name=m.get("display_name") or mid,
                            description=f"Anthropic Claude ({mid})",
                            context_window=m.get("max_input_tokens") or 200_000,
                            max_output_tokens=m.get("max_tokens"),
                            supported_methods=["messages"],
                            capabilities=caps,
                            lifecycle_status=lifecycle,
                            raw_metadata=m,
                        )
                    )
                if not data.get("has_more"):
                    break
                after_id = data.get("last_id")
                if not after_id:
                    break
        return models

    async def test_connection(self, api_key: str) -> ConnectionTestResult:
        if not api_key:
            return ConnectionTestResult(success=False, status="Configuration Required", message="API Key não informada.")
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(f"{self.BASE_URL}/models", headers=self._headers(api_key), params={"limit": 20})
            latency = int((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                count = len(resp.json().get("data", []))
                return ConnectionTestResult(
                    success=True,
                    status="Connected",
                    latency_ms=latency,
                    models_count=count,
                    message=f"Conectado à Anthropic Claude ({count} modelos na primeira página).",
                )
            st, msg = _classify_http_error(resp.status_code, resp.text)
            return ConnectionTestResult(success=False, status=st, latency_ms=latency, error_code=str(resp.status_code), message=msg)
        except Exception as e:
            return ConnectionTestResult(success=False, status="Connection Error", message=str(e))

    async def generate(
        self,
        api_key: str,
        model_id: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.4,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AdapterGenerationResult:
        t0 = time.monotonic()
        messages = []
        if history:
            for h in history[-6:]:
                messages.append({"role": "user", "content": str(h.get("text", ""))[:2000]})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model_id,
            "max_tokens": 2048,
            "temperature": temperature,
            "messages": messages,
        }
        if system_instruction:
            payload["system"] = system_instruction

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.BASE_URL}/messages", headers=self._headers(api_key), json=payload)
        latency = int((time.monotonic() - t0) * 1000)
        if resp.status_code != 200:
            st, msg = _classify_http_error(resp.status_code, resp.text)
            raise RuntimeError(f"Anthropic {st}: {msg}")

        data = resp.json()
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        usage = data.get("usage", {})
        in_tok = int(usage.get("input_tokens", 0))
        out_tok = int(usage.get("output_tokens", 0))
        cached_tok = int(usage.get("cache_read_input_tokens", 0))
        return AdapterGenerationResult(
            content=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cached_tokens=cached_tok,
            total_tokens=in_tok + out_tok,
            model_id=model_id,
            provider="anthropic",
            duration_ms=latency,
        )


def get_provider_adapter(provider: str):
    p = provider.lower()
    if p == "gemini":
        return GeminiAdapter()
    if p == "openai":
        return OpenAIAdapter()
    if p == "anthropic":
        return AnthropicAdapter()
    raise ValueError(f"Provedor não suportado: {provider}")

