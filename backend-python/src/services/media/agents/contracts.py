from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class AgentStage(str, Enum):
    SCRIPT = "script"
    VIDEO_SCENES = "video_scenes"
    NARRATION = "narration"
    SUBTITLES = "subtitles"
    ASSEMBLE = "assemble"


STAGE_ORDER: List[AgentStage] = [
    AgentStage.SCRIPT,
    AgentStage.VIDEO_SCENES,
    AgentStage.NARRATION,
    AgentStage.SUBTITLES,
    AgentStage.ASSEMBLE,
]

STAGE_METADATA: Dict[str, Dict[str, Any]] = {
    AgentStage.SCRIPT.value: {
        "order": 1,
        "agent_action": "agent_script",
        "label": "Agente 1 · Roteiros Completos",
        "short_label": "1. Roteiro",
        "description": "Cria gancho, narrativa natural com ritmo calibrado, bíblia visual adaptativa e direção de câmera.",
    },
    AgentStage.VIDEO_SCENES.value: {
        "order": 2,
        "agent_action": "agent_video_scenes",
        "label": "Agente 2 · Geração de Vídeo & Cenas",
        "short_label": "2. Vídeo/Cenas",
        "description": "Gera as cenas 9:16 via Google Gemini mantendo consistência visual e preparando movimento de câmera.",
    },
    AgentStage.NARRATION.value: {
        "order": 3,
        "agent_action": "agent_narration",
        "label": "Agente 3 · Geração de Narração",
        "short_label": "3. Narração",
        "description": "Normaliza texto PT-BR e sintetiza locução natural cena a cena com timestamps reais e loudness.",
    },
    AgentStage.SUBTITLES.value: {
        "order": 4,
        "agent_action": "agent_subtitles",
        "label": "Agente 4 · Geração de Legenda",
        "short_label": "4. Legendas",
        "description": "Constrói blocos prosódicos e legendas .ass/.srt com destaque palavra-a-palavra sincronizado.",
    },
    AgentStage.ASSEMBLE.value: {
        "order": 5,
        "agent_action": "agent_assemble_video",
        "label": "Agente 5 · Montagem & Render Final",
        "short_label": "5. Montagem",
        "description": "Aplica movimento Ken Burns, transições suaves, queima legendas e valida o MP4 final via FFprobe.",
    },
}


class VisualBibleSpec(BaseModel):
    protagonist_description: str = ""
    world_setting: str = ""
    color_palette: str = ""
    art_style: str = "cinematic film still, atmospheric volumetric lighting, sharp focus"
    lighting_mood: str = "dramatic chiaroscuro lighting"
    negative_constraints: str = "no watermark, no text overlay, no split screen, no distorted anatomy"


class ScriptSceneSpec(BaseModel):
    scene_number: int
    act: str = "development"
    narration: str
    speech_text_tts: str = ""
    estimated_seconds: float = 3.0
    visual_prompt_en: str
    include_character: bool = True
    camera_angle: str = "medium cinematic shot"
    camera_motion: Literal["zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up"] = "zoom_in"
    on_screen_text: str = ""


class ScriptArtifact(BaseModel):
    title: str
    topic: str = ""
    format_type: Literal["short", "long"] = "short"
    target_platform: str = "youtube_shorts"
    hook: str = ""
    cta: str = ""
    full_narration: str = ""
    voice_persona: str = "pt-BR-AntonioNeural"
    seo_tags: List[str] = Field(default_factory=list)
    visual_bible: VisualBibleSpec = Field(default_factory=VisualBibleSpec)
    scenes: List[ScriptSceneSpec] = Field(default_factory=list)
    word_count: int = 0
    estimated_total_seconds: float = 0.0
    quality_notes: List[str] = Field(default_factory=list)


class SceneVisualAsset(BaseModel):
    scene_number: int
    asset_type: Literal["image", "video_clip"] = "image"
    file_path: str
    url: str = ""
    width: int = 1080
    height: int = 1920
    provider: str = "google_gemini"
    camera_motion: str = "zoom_in"
    include_character: bool = True
    vision_verified: bool = False
    regenerated_count: int = 0


class ScenesArtifact(BaseModel):
    assets: List[SceneVisualAsset] = Field(default_factory=list)
    provider_primary: str = "google_gemini"
    story_seed: int = 424242
    total_scenes: int = 0


class NarrationSegment(BaseModel):
    scene_number: int
    audio_path: str
    duration_seconds: float
    text_spoken: str
    word_timings: List[Dict[str, Any]] = Field(default_factory=list)


class NarrationArtifact(BaseModel):
    master_audio_path: str
    url: str = ""
    total_duration_seconds: float = 0.0
    provider: str = "edge_tts"
    voice_id: str = "pt-BR-AntonioNeural"
    rate_used: str = "+4%"
    segments: List[NarrationSegment] = Field(default_factory=list)
    word_timings: List[Dict[str, Any]] = Field(default_factory=list)
    scene_durations: List[float] = Field(default_factory=list)


class SubtitleArtifact(BaseModel):
    srt_path: str
    ass_path: str
    srt_url: str = ""
    chunks_count: int = 0
    events_count: int = 0
    style_preset: str = "hormozi_karaoke"
    sync_warnings: List[str] = Field(default_factory=list)


class FinalVideoArtifact(BaseModel):
    video_path: str
    url: str = ""
    resolution: str = "1080x1920"
    aspect_ratio: str = "9:16"
    duration_seconds: float = 0.0
    size_mb: float = 0.0
    motion_applied: bool = True
    ffprobe_verified: bool = True


class PipelineManifest(BaseModel):
    task_id: int
    business_id: int
    title: str
    pause_after_script: bool = True
    current_stage: str = AgentStage.SCRIPT.value
    stage_statuses: Dict[str, str] = Field(
        default_factory=lambda: {s.value: "pending" for s in STAGE_ORDER}
    )
    script: Optional[ScriptArtifact] = None
    scenes_visual: Optional[ScenesArtifact] = None
    narration: Optional[NarrationArtifact] = None
    subtitles: Optional[SubtitleArtifact] = None
    final_video: Optional[FinalVideoArtifact] = None
    errors: Dict[str, str] = Field(default_factory=dict)

