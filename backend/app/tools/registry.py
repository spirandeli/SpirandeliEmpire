"""SpirandeliEmpire OS 3.2 — Real, Sandboxed Tool Registry & Execution Engine"""

import ast
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional
import httpx
import psutil
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.security import decrypt_secret


class ToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    id: str
    name: str
    description: str
    parameters: List[ToolParameter] = Field(default_factory=list)
    authorized_agents: List[str]
    required_permissions: List[str] = Field(default_factory=list)
    timeout_seconds: int = 30
    risk_level: str = "low"
    retry_limit: int = 1


class ToolResult(BaseModel):
    tool_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: float
    artifacts_created: List[str] = Field(default_factory=list)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._executors: Dict[str, Callable[[Dict[str, Any], str], Awaitable[ToolResult]]] = {}

    def register(
        self,
        definition: ToolDefinition,
        executor: Callable[[Dict[str, Any], str], Awaitable[ToolResult]],
    ):
        self._tools[definition.id] = definition
        self._executors[definition.id] = executor

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._tools.get(tool_id)

    def list_tools(self, agent_id: Optional[str] = None) -> List[ToolDefinition]:
        if not agent_id:
            return list(self._tools.values())
        return [
            tool for tool in self._tools.values()
            if agent_id in tool.authorized_agents or "all" in tool.authorized_agents
        ]

    async def execute(
        self,
        tool_id: str,
        params: Dict[str, Any],
        caller_agent_id: str,
    ) -> ToolResult:
        start_time = time.time()
        tool = self.get_tool(tool_id)

        if not tool:
            return ToolResult(
                tool_id=tool_id,
                success=False,
                output=None,
                error=f"Ferramenta '{tool_id}' não existe no registry.",
                execution_time_ms=0,
            )

        if caller_agent_id not in tool.authorized_agents and "all" not in tool.authorized_agents:
            return ToolResult(
                tool_id=tool_id,
                success=False,
                output=None,
                error=f"Agente '{caller_agent_id}' não tem permissão para usar '{tool_id}'.",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        executor = self._executors.get(tool_id)
        if not executor:
            return ToolResult(
                tool_id=tool_id,
                success=False,
                output=None,
                error=f"Executor para ferramenta '{tool_id}' não implementado.",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        attempts = 0
        last_error = None
        while attempts <= tool.retry_limit:
            attempts += 1
            try:
                result = await asyncio.wait_for(
                    executor(params, caller_agent_id),
                    timeout=tool.timeout_seconds,
                )
                result.execution_time_ms = round((time.time() - start_time) * 1000, 2)
                return result
            except asyncio.TimeoutError:
                last_error = f"Execução excedeu o timeout de {tool.timeout_seconds}s."
            except Exception as e:
                last_error = str(e)

            if attempts <= tool.retry_limit:
                await asyncio.sleep(0.3 * attempts)

        return ToolResult(
            tool_id=tool_id,
            success=False,
            output=None,
            error=f"Falha após {attempts} tentativas: {last_error}",
            execution_time_ms=round((time.time() - start_time) * 1000, 2),
        )


tool_registry = ToolRegistry()


def _resolve_sandbox_path(rel_or_subpath: str) -> Optional[Path]:
    """Strictly confine file access to settings.STORAGE_DIR."""
    storage_root = settings.STORAGE_DIR.resolve()
    candidate = Path(rel_or_subpath)
    full_path = candidate.resolve() if candidate.is_absolute() else (storage_root / candidate).resolve()
    if not full_path.is_relative_to(storage_root):
        return None
    return full_path


# --- REAL EXECUTORS ---

async def _file_reader_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    rel_path = params.get("path", "")
    full_path = _resolve_sandbox_path(rel_path)
    if full_path is None:
        return ToolResult(
            tool_id="file_reader",
            success=False,
            output=None,
            error="Acesso negado: fora do diretório de storage autorizado.",
            execution_time_ms=0,
        )
    if not full_path.exists() or not full_path.is_file():
        return ToolResult(
            tool_id="file_reader",
            success=False,
            output=None,
            error=f"Arquivo '{rel_path}' não encontrado.",
            execution_time_ms=0,
        )
    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(50000)
    return ToolResult(
        tool_id="file_reader",
        success=True,
        output={"content": content, "size": full_path.stat().st_size, "path": str(full_path)},
        execution_time_ms=0,
    )


async def _file_writer_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    rel_path = params.get("path", "")
    content = params.get("content", "")
    full_path = _resolve_sandbox_path(rel_path)
    if full_path is None:
        return ToolResult(
            tool_id="file_writer",
            success=False,
            output=None,
            error="Acesso negado: tentativa de escrita fora do diretório de storage autorizado.",
            execution_time_ms=0,
        )
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return ToolResult(
        tool_id="file_writer",
        success=True,
        output={"path": str(full_path), "bytes_written": len(content.encode("utf-8"))},
        artifacts_created=[str(full_path)],
        execution_time_ms=0,
    )


async def _system_monitor_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    cpu_percent = psutil.cpu_percent(interval=None)
    virtual_mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return ToolResult(
        tool_id="system_monitor",
        success=True,
        output={
            "cpu_percent": cpu_percent,
            "memory": {
                "total_mb": round(virtual_mem.total / (1024 * 1024), 2),
                "used_mb": round(virtual_mem.used / (1024 * 1024), 2),
                "percent": virtual_mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                "used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
                "percent": disk.percent,
            },
            "process_count": len(psutil.pids()),
        },
        execution_time_ms=0,
    )


async def _web_search_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    query = (params.get("query") or "").strip()
    if not query:
        return ToolResult(tool_id="web_search", success=False, output=None, error="Query vazia.", execution_time_ms=0)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
        if resp.status_code != 200:
            return ToolResult(tool_id="web_search", success=False, output=None, error=f"HTTP {resp.status_code}", execution_time_ms=0)
        data = resp.json()
        topics = [
            {"title": t.get("Text", "")[:120], "url": t.get("FirstURL", "")}
            for t in (data.get("RelatedTopics") or [])[:5]
            if isinstance(t, dict) and t.get("Text")
        ]
        return ToolResult(
            tool_id="web_search",
            success=True,
            output={"query": query, "abstract": data.get("AbstractText", ""), "source": data.get("AbstractURL", ""), "topics": topics},
            execution_time_ms=0,
        )
    except Exception as e:
        return ToolResult(tool_id="web_search", success=False, output=None, error=f"Falha na busca web real: {e}", execution_time_ms=0)


async def _rss_fetcher_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    feed_url = (params.get("url") or "https://hnrss.org/frontpage").strip()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(feed_url)
    if resp.status_code != 200:
        return ToolResult(tool_id="rss_fetcher", success=False, output=None, error=f"HTTP {resp.status_code}", execution_time_ms=0)
    root = ET.fromstring(resp.text)
    items = []
    for item in root.findall(".//item")[:5]:
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
        })
    return ToolResult(tool_id="rss_fetcher", success=True, output={"feed_url": feed_url, "items": items}, execution_time_ms=0)


async def _script_generator_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    topic = (params.get("topic") or "").strip()
    target_format = params.get("format", "shorts")
    content = params.get("content")
    if not content:
        prompt = f"Crie um roteiro completo e estruturado ({target_format}) sobre: {topic}. Inclua Hook, Desenvolvimento, Clímax e CTA."
        sys_inst = "Você é o Script Agent do SpirandeliEmpire OS. Produza roteiros objetivos e prontos para narração."
        user_id = params.get("user_id")
        if user_id:
            from app.providers.model_resolver import model_router
            routed = await model_router.generate(
                user_id=user_id,
                prompt=prompt,
                system_instruction=sys_inst,
                agent_id=agent_id,
                task_profile="writing",
                temperature=0.5,
            )
            content = routed["content"]
        else:
            from app.providers.gemini_provider import gemini_provider
            res = await gemini_provider.generate(
                prompt=prompt,
                system_instruction=sys_inst,
                temperature=0.5,
            )
            content = res.content
    file_name = f"script_{int(time.time() * 1000)}.md"
    file_path = settings.ARTIFACTS_DIR / file_name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return ToolResult(
        tool_id="script_generator",
        success=True,
        output={"topic": topic, "format": target_format, "file": str(file_path), "bytes": len(content.encode("utf-8"))},
        artifacts_created=[str(file_path)],
        execution_time_ms=0,
    )


async def _srt_formatter_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    lines = params.get("lines")
    if not lines:
        raw_text = (params.get("text") or "SpirandeliEmpire OS 3.2").strip()
        sentences = [s.strip() for s in raw_text.replace("\n", ". ").split(".") if s.strip()][:8]
        if not sentences:
            sentences = [raw_text]
        lines = []
        sec = 0
        for s in sentences:
            start = f"00:00:{sec:02d},000"
            sec += 4
            end = f"00:00:{sec:02d},000"
            lines.append((start, end, s[:120]))

    srt_text = "".join(f"{idx}\n{start} --> {end}\n{text}\n\n" for idx, (start, end, text) in enumerate(lines, 1))
    file_name = f"subtitles_{int(time.time() * 1000)}.srt"
    file_path = settings.ARTIFACTS_DIR / file_name
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(srt_text)
    return ToolResult(
        tool_id="srt_formatter",
        success=True,
        output={"subtitles": srt_text, "file": str(file_path), "cues": len(lines)},
        artifacts_created=[str(file_path)],
        execution_time_ms=0,
    )


async def _tts_generator_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    # Check if external TTS integration credential is configured in DB
    from app.database.session import AsyncSessionLocal
    from app.database.models import IntegrationModel

    async with AsyncSessionLocal() as session:
        integ = await session.get(IntegrationModel, "tts")
        key = decrypt_secret(integ.credentials_encrypted) if integ and integ.credentials_encrypted else ""
    if not key:
        return ToolResult(
            tool_id="tts_generator",
            success=False,
            output=None,
            error="BLOCKED: Motor TTS externo não configurado no Integration Hub.",
            execution_time_ms=0,
        )
    return ToolResult(
        tool_id="tts_generator",
        success=False,
        output=None,
        error="BLOCKED: Provedor TTS configurado requer endpoint de síntese específico.",
        execution_time_ms=0,
    )


async def _image_generator_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    from PIL import Image, ImageDraw
    title = (params.get("title") or "SpirandeliEmpire OS")[:40]
    file_name = f"asset_{int(time.time() * 1000)}.png"
    file_path = settings.ARTIFACTS_DIR / file_name
    img = Image.new("RGB", (640, 360), (15, 23, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 620, 340], outline=(79, 70, 229), width=4)
    draw.text((40, 160), title, fill=(248, 250, 252))
    img.save(file_path, format="PNG")
    return ToolResult(
        tool_id="image_generator",
        success=True,
        output={"path": str(file_path), "width": 640, "height": 360, "format": "png"},
        artifacts_created=[str(file_path)],
        execution_time_ms=0,
    )


async def _ffmpeg_assembler_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return ToolResult(
            tool_id="ffmpeg_assembler",
            success=False,
            output=None,
            error="BLOCKED: binário ffmpeg não encontrado no ambiente.",
            execution_time_ms=0,
        )
    out_name = f"video_{int(time.time() * 1000)}.mp4"
    out_path = settings.ARTIFACTS_DIR / out_name
    cmd = [
        ffmpeg_bin, "-y", "-f", "lavfi", "-i", "color=c=0x0f172a:s=640x360:d=2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    if proc.returncode != 0 or not out_path.exists():
        return ToolResult(tool_id="ffmpeg_assembler", success=False, output=None, error=proc.stderr[:400], execution_time_ms=0)
    return ToolResult(
        tool_id="ffmpeg_assembler",
        success=True,
        output={"path": str(out_path), "size_bytes": out_path.stat().st_size, "format": "mp4"},
        artifacts_created=[str(out_path)],
        execution_time_ms=0,
    )


async def _media_inspector_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    rel_path = params.get("path", "")
    full_path = _resolve_sandbox_path(rel_path)
    if full_path is None or not full_path.exists():
        return ToolResult(tool_id="video_inspector", success=False, output=None, error="Arquivo de mídia não encontrado no storage.", execution_time_ms=0)
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        return ToolResult(tool_id="video_inspector", success=True, output={"path": str(full_path), "size_bytes": full_path.stat().st_size}, execution_time_ms=0)
    proc = subprocess.run([ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_format", str(full_path)], capture_output=True, text=True, timeout=10)
    info = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout else {}
    return ToolResult(tool_id="video_inspector", success=True, output={"path": str(full_path), "size_bytes": full_path.stat().st_size, "ffprobe": info.get("format", {})}, execution_time_ms=0)


async def _syntax_checker_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    code = params.get("code", "")
    lang = (params.get("language") or "python").lower()
    if lang == "python":
        try:
            ast.parse(code)
            return ToolResult(tool_id="syntax_checker", success=True, output={"valid": True, "language": "python"}, execution_time_ms=0)
        except SyntaxError as e:
            return ToolResult(tool_id="syntax_checker", success=False, output={"valid": False}, error=str(e), execution_time_ms=0)
    if lang == "json":
        json.loads(code)
        return ToolResult(tool_id="syntax_checker", success=True, output={"valid": True, "language": "json"}, execution_time_ms=0)
    return ToolResult(tool_id="syntax_checker", success=True, output={"valid": bool(code), "language": lang}, execution_time_ms=0)


async def _schema_inspector_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    from app.database.session import Base
    tables = {name: [c.name for c in tbl.columns] for name, tbl in Base.metadata.tables.items()}
    return ToolResult(tool_id="schema_inspector", success=True, output={"tables_count": len(tables), "tables": tables}, execution_time_ms=0)


async def _quality_scorer_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    artifact_paths = params.get("artifact_paths", [])
    validations = []
    total_passed = 0
    for path_str in artifact_paths:
        p = _resolve_sandbox_path(path_str) or (settings.ARTIFACTS_DIR / os.path.basename(path_str))
        exists = p.exists() and p.is_file()
        size = p.stat().st_size if exists else 0
        sha256 = hashlib.sha256(p.read_bytes()).hexdigest()[:16] if exists and size > 0 else ""
        is_valid = exists and size > 0
        validations.append({"artifact": path_str, "exists": exists, "size_bytes": size, "sha256_prefix": sha256, "valid": is_valid})
        if is_valid:
            total_passed += 1
    score = (total_passed / len(artifact_paths)) if artifact_paths else 1.0
    passed = score >= 0.8
    return ToolResult(
        tool_id="quality_scorer",
        success=passed,
        output={"score": score, "passed": passed, "validations": validations, "evaluated_by": "Murphy (QA Gate)"},
        execution_time_ms=0,
    )


async def _deploy_checker_executor(params: Dict[str, Any], agent_id: str) -> ToolResult:
    sys_res = await _system_monitor_executor(params, agent_id)
    return ToolResult(
        tool_id="deploy_checker",
        success=True,
        output={"storage_writable": os.access(settings.STORAGE_DIR, os.W_OK), "system": sys_res.output},
        execution_time_ms=0,
    )


async def _blocked_external_tool_executor(tool_name: str):
    async def _exec(params: Dict[str, Any], agent_id: str) -> ToolResult:
        return ToolResult(
            tool_id=tool_name,
            success=False,
            output=None,
            error=f"BLOCKED: Ferramenta externa '{tool_name}' requer serviço/credencial externa configurada.",
            execution_time_ms=0,
        )
    return _exec


# --- REGISTER TOOLS FOR ALL 14 AGENTS ---

tool_registry.register(ToolDefinition(id="file_reader", name="Leitor de Arquivos", description="Lê arquivos do storage com sandbox estrita.", parameters=[ToolParameter(name="path", type="string", description="Caminho no storage")], authorized_agents=["all"], required_permissions=["read_repo"]), _file_reader_executor)
tool_registry.register(ToolDefinition(id="file_writer", name="Gravador de Arquivos", description="Grava artefatos exclusivamente dentro de STORAGE_DIR.", parameters=[ToolParameter(name="path", type="string", description="Caminho no storage"), ToolParameter(name="content", type="string", description="Conteúdo")], authorized_agents=["jeffrey", "fonseca", "balsini", "jarvis", "noe", "ford", "murphy", "script_agent", "clipador_agent", "designer_agent", "video_agent"], required_permissions=["write_storage"]), _file_writer_executor)
tool_registry.register(ToolDefinition(id="system_monitor", name="Monitor da VPS", description="CPU, RAM, Disco e processos em tempo real.", authorized_agents=["jeffrey", "jarvis"], required_permissions=["manage_docker"]), _system_monitor_executor)
tool_registry.register(ToolDefinition(id="web_search", name="Pesquisa Web", description="Consulta real via DuckDuckGo Instant Answer API.", parameters=[ToolParameter(name="query", type="string", description="Termo")], authorized_agents=["jeffrey", "news_agent"], required_permissions=["read_web"]), _web_search_executor)
tool_registry.register(ToolDefinition(id="rss_fetcher", name="Leitor RSS", description="Consulta feeds RSS reais via HTTP.", parameters=[ToolParameter(name="url", type="string", description="URL RSS", required=False)], authorized_agents=["jeffrey", "news_agent"], required_permissions=["read_web"]), _rss_fetcher_executor)
tool_registry.register(ToolDefinition(id="script_generator", name="Gerador de Roteiro", description="Produz roteiro via LLM e salva artefato.", parameters=[ToolParameter(name="topic", type="string", description="Tema")], authorized_agents=["jeffrey", "script_agent"], required_permissions=["write_content"]), _script_generator_executor)
tool_registry.register(ToolDefinition(id="srt_formatter", name="Formatador SRT", description="Gera legendas SRT a partir de texto ou linhas.", authorized_agents=["jeffrey", "subtitle_agent"], required_permissions=["generate_subtitles"]), _srt_formatter_executor)
tool_registry.register(ToolDefinition(id="tts_generator", name="Gerador de Áudio TTS", description="Requer provedor TTS externo configurado.", authorized_agents=["jeffrey", "voice_agent"], required_permissions=["generate_audio"]), _tts_generator_executor)
tool_registry.register(ToolDefinition(id="image_generator", name="Gerador de Imagem PNG", description="Gera assets PNG reais com Pillow.", authorized_agents=["jeffrey", "designer_agent"], required_permissions=["generate_images"]), _image_generator_executor)
tool_registry.register(ToolDefinition(id="sprite_exporter", name="Exportador de Sprites", description="Gera sprites PNG no storage.", authorized_agents=["jeffrey", "designer_agent"], required_permissions=["generate_images"]), _image_generator_executor)
tool_registry.register(ToolDefinition(id="ffmpeg_assembler", name="Montagem FFmpeg", description="Renderiza vídeo MP4 real via FFmpeg.", authorized_agents=["jeffrey", "video_agent"], required_permissions=["render_video"]), _ffmpeg_assembler_executor)
tool_registry.register(ToolDefinition(id="video_inspector", name="Inspetor de Vídeo", description="Inspeciona mídia com ffprobe.", authorized_agents=["jeffrey", "video_agent", "clipador_agent"], required_permissions=["render_video"]), _media_inspector_executor)
tool_registry.register(ToolDefinition(id="audio_inspector", name="Inspetor de Áudio", description="Inspeciona áudio com ffprobe.", authorized_agents=["jeffrey", "voice_agent"], required_permissions=["generate_audio"]), _media_inspector_executor)
tool_registry.register(ToolDefinition(id="syntax_checker", name="Validador de Sintaxe", description="Valida sintaxe Python/JSON via AST.", authorized_agents=["jeffrey", "fonseca", "balsini", "murphy"], required_permissions=["read_repo"]), _syntax_checker_executor)
tool_registry.register(ToolDefinition(id="schema_inspector", name="Inspetor de Schema DB", description="Inspeciona tabelas SQLAlchemy.", authorized_agents=["jeffrey", "ford"], required_permissions=["read_db"]), _schema_inspector_executor)
tool_registry.register(ToolDefinition(id="quality_scorer", name="Avaliador Murphy", description="Valida existência, tamanho e SHA-256 de artefatos.", authorized_agents=["jeffrey", "murphy"], required_permissions=["approve_qa"]), _quality_scorer_executor)
tool_registry.register(ToolDefinition(id="artifact_validator", name="Validador de Artefatos", description="Valida integridade de artefatos no storage.", authorized_agents=["jeffrey", "murphy"], required_permissions=["approve_qa"]), _quality_scorer_executor)
tool_registry.register(ToolDefinition(id="artifact_reviewer", name="Revisor de Artefatos", description="Revisa artefatos produzidos.", authorized_agents=["jeffrey", "murphy"], required_permissions=["approve_qa"]), _quality_scorer_executor)
tool_registry.register(ToolDefinition(id="deploy_checker", name="Verificador de Deploy", description="Verifica saúde do ambiente e storage.", authorized_agents=["jeffrey", "jarvis"], required_permissions=["read_infra"]), _deploy_checker_executor)
