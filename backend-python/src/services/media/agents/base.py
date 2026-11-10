import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, Optional

from src.services.media.agents.contracts import AgentStage, PipelineManifest
from src.services.media.media_settings import get_task_media_dir, get_task_output_dir

logger = logging.getLogger("abvos.media.agents")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class AgentContext:
    task_id: int
    business_id: int
    user_id: int
    title: str
    topic: str = ""
    context_text: str = ""
    business_name: str = ""
    business_niche: str = ""
    business_archetype: str = ""
    brand_rules: Dict[str, Any] = field(default_factory=dict)
    format_type: str = "short"
    target_platform: str = "youtube_shorts"
    tone: str = "Envolvente, claro e cinematográfico"
    visual_style: str = ""
    voice_persona: str = ""
    gemini_key: str = ""
    elevenlabs_key: str = ""
    pause_after_script: bool = True
    progress_cb: Optional[Callable[[str, float, str], Coroutine[Any, Any, None]]] = None

    @property
    def media_dir(self) -> Path:
        return get_task_media_dir(self.business_id, self.task_id)

    @property
    def output_dir(self) -> Path:
        return get_task_output_dir(self.business_id, self.task_id)

    @property
    def manifest_path(self) -> Path:
        return self.media_dir / "pipeline_manifest.json"


def load_manifest(ctx: AgentContext) -> PipelineManifest:
    if ctx.manifest_path.exists():
        try:
            raw = json.loads(ctx.manifest_path.read_text(encoding="utf-8"))
            return PipelineManifest.model_validate(raw)
        except Exception as exc:
            logger.warning(f"[Task #{ctx.task_id}] Falha ao ler manifest.json existente ({exc}); recriando.")
    return PipelineManifest(
        task_id=ctx.task_id,
        business_id=ctx.business_id,
        title=ctx.title,
        pause_after_script=ctx.pause_after_script,
    )


def save_manifest(ctx: AgentContext, manifest: PipelineManifest) -> Path:
    ctx.media_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = ctx.manifest_path.with_suffix(".json.tmp")
    tmp_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    tmp_path.replace(ctx.manifest_path)
    return ctx.manifest_path


class BaseMediaAgent:
    stage: AgentStage

    async def notify(self, ctx: AgentContext, percent: float, message: str) -> None:
        if ctx.progress_cb:
            try:
                await ctx.progress_cb(self.stage.value, percent, message)
            except Exception as exc:
                logger.warning(f"[{self.__class__.__name__}] Callback de progresso falhou: {exc}")

    async def run(self, ctx: AgentContext, manifest: PipelineManifest) -> PipelineManifest:
        raise NotImplementedError

