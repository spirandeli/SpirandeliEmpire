import asyncio
import functools
import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.services.media.media_settings import (
    get_task_media_dir,
    get_task_output_dir,
    STORAGE_OUTPUT_DIR,
)
from src.services.media.image_service import (
    generate_all_scene_images,
    create_cinematic_dark_backdrop,
)
from src.services.media.tts_service import synthesize_narration, clean_narration_for_tts
from src.services.media.subtitle_service import generate_subtitles, compute_scene_timings_from_words
from src.services.media.video_renderer import render_video_with_audio_and_subtitles

logger = logging.getLogger("abvos.media.pipeline")


class TaskRouter:
    """
    Router de tarefas assíncronas do motor ABVOS (compatível com ARQ, Celery e FastAPI Background).
    Permite registrar tasks com decorators contendo job_timeout e metadados de execução.
    """
    def __init__(self):
        self._tasks: Dict[str, Any] = {}

    def task(self, job_timeout: Optional[int] = None, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kw):
                if args and (isinstance(args[0], dict) or hasattr(args[0], "redis")):
                    return await func(*args[1:], **kw)
                return await func(*args, **kw)

            wrapper.job_timeout = job_timeout
            wrapper.task_kwargs = kwargs
            wrapper._raw_func = func
            self._tasks[func.__name__] = wrapper
            return wrapper
        return decorator

    def get_task(self, name: str):
        return self._tasks.get(name)

    @property
    def registered_tasks(self) -> Dict[str, Any]:
        return self._tasks


router = TaskRouter()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _persist_video_progress(
    task_id: int,
    business_id: int,
    current_scene: int = 0,
    total_scenes: int = 20,
    status_text: Optional[str] = None,
    percent: Optional[float] = None,
    stage: Optional[str] = None,
    is_completed: bool = False,
    output_path: Optional[str] = None,
):
    """
    Atualiza o progresso no banco de dados (tabela tasks, campos status_log, description, status e payload)
    em tempo real para refletir a pipeline no Kanban:
    - Iniciando geração de prompts... (0%)
    - Gerando imagens (Cena 5/20)... (25%)
    - Gerando áudio TTS (ElevenLabs)... (50%)
    - Renderizando vídeo via FFmpeg... (80%)
    - Concluído. Arquivo salvo em /app/storage/output/ (100%)
    """
    if percent is None:
        if is_completed or stage == "done":
            percent = 100.0
        elif stage == "prompts":
            percent = 0.0
        elif stage == "tts":
            percent = 50.0
        elif stage == "ffmpeg":
            percent = 80.0
        elif stage == "images" or current_scene > 0:
            percent = round((current_scene / total_scenes) * 100, 1) if total_scenes else 0.0
        else:
            percent = 0.0

    if not status_text:
        if percent == 0 or stage == "prompts":
            status_text = "Iniciando geração de prompts..."
        elif stage == "images":
            status_text = f"Gerando imagens (Cena {current_scene}/{total_scenes})..."
        elif stage == "tts" or percent == 50:
            status_text = "Gerando áudio TTS (ElevenLabs)..."
        elif stage == "ffmpeg" or percent == 80:
            status_text = "Renderizando vídeo via FFmpeg..."
        elif is_completed or percent == 100 or stage == "done":
            status_text = f"Concluído. Arquivo salvo em {output_path or '/app/storage/output/'}"
        else:
            status_text = f"Processando vídeo ({current_scene}/{total_scenes})..."

    formatted_msg = f"{status_text} ({int(percent)}%)" if not status_text.endswith("%)") else status_text

    try:
        from src.database import AsyncSessionLocal
        from src.models import Task, AgentLog
        from sqlalchemy.future import select

        now = _utc_now()

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Task).where(Task.id == task_id))
            task = res.scalar_one_or_none()
            if task:
                task.status_log = formatted_msg

                orig_desc = task.description or ""
                clean_lines = [
                    l for l in orig_desc.splitlines()
                    if not re.match(r"^(?:\[Progresso|\b(?:Iniciando|Gerando|Renderizando|Concluído).*?\(\d+%\))", l.strip(), re.IGNORECASE)
                ]
                clean_orig = "\n".join(clean_lines).strip()
                task.description = f"{formatted_msg}\n\n{clean_orig}".strip() if clean_orig else formatted_msg

                payload_data = dict(task.payload or {})
                payload_data["video_progress"] = {
                    "stage": stage or ("done" if is_completed else "running"),
                    "current_scene": current_scene,
                    "total_scenes": total_scenes,
                    "percent": percent,
                    "status_log": formatted_msg,
                    "output_path": output_path or "/app/storage/output/",
                    "updated_at": now.isoformat(),
                }
                task.payload = payload_data
                task.updated_at = now

                if is_completed or percent >= 100:
                    task.status = "done"
                    task.completed_at = now

                agent_log = AgentLog(
                    user_id=task.user_id,
                    business_id=task.business_id or business_id,
                    task_id=task.id,
                    level="info",
                    event="video_scene_progress",
                    message=f"IA Worker ABVOS: {formatted_msg}",
                    context={
                        "task_id": task.id,
                        "current_scene": current_scene,
                        "total_scenes": total_scenes,
                        "percent": percent,
                        "stage": stage,
                    },
                    created_at=now,
                )
                session.add(agent_log)
                await session.commit()
                logger.info(f"[Task #{task_id}] Progresso persistido no banco: {formatted_msg}")
    except Exception as db_err:
        logger.warning(f"[Task #{task_id}] Falha não-bloqueante ao persistir progresso no banco: {db_err}")


def _build_narrative_beats(title: str) -> List[Dict[str, str]]:
    """
    Retorna 20 batidas narrativas contínuas (em português natural sem marcadores técnicos,
    6 a 8 palavras por cena para ritmo ideal de 60s) e prompts visuais distintos em inglês
    quando o roteiro de entrada tiver menos de 20 cenas.
    """
    clean_topic = clean_narration_for_tts(title) or "esse mistério ancestral"
    short_topic = " ".join(clean_topic.split()[:5])
    return [
        {
            "narration": f"Um segredo antigo sobre {short_topic} estava selado.",
            "visual_prompt": f"Silhouette of a celestial winged archangel standing before a cosmic rift, {short_topic}, dark anime style, volumetric light, 9:16",
        },
        {
            "narration": "Poucos ousaram olhar além do véu proibido.",
            "visual_prompt": f"Ancient forbidden temple gates opening into glowing abyssal fog, {short_topic}, dramatic chiaroscuro lighting, 9:16",
        },
        {
            "narration": "As escrituras descreviam um poder sem limites.",
            "visual_prompt": f"Close up on ancient glowing golden scriptures floating in dark air with burning embers, {short_topic}, dark fantasy art, 9:16",
        },
        {
            "narration": "Mas existia um preço oculto naquela escolha.",
            "visual_prompt": f"Lone hooded watcher looking at a colossal eclipsed sun over gothic ruins, {short_topic}, dark epic anime, 9:16",
        },
        {
            "narration": "No santuário profundo, o primeiro sinal despertou.",
            "visual_prompt": f"Subterranean obsidian throne room illuminated by crimson and gold lightning, {short_topic}, Unreal Engine 5 cinematic, 9:16",
        },
        {
            "narration": "A antiga lenda revelou sua verdadeira face.",
            "visual_prompt": f"Majestic warrior angel with glowing sapphire eyes emerging from shadows, {short_topic}, hyper-detailed dark anime, 9:16",
        },
        {
            "narration": "Tudo foi planejado em silêncio por séculos.",
            "visual_prompt": f"Intricate celestial clockwork gears and astral constellations spinning in darkness, {short_topic}, dramatic rim light, 9:16",
        },
        {
            "narration": "Quando notaram a mudança, tudo havia ruído.",
            "visual_prompt": f"Two rival celestial figures clashing in mid-air above storm clouds, {short_topic}, dynamic action angle, dark anime, 9:16",
        },
        {
            "narration": "O céu escureceu e o abismo respondeu.",
            "visual_prompt": f"Dark vortex tearing through the night sky above an ancient citadel, {short_topic}, ominous atmospheric fog, 9:16",
        },
        {
            "narration": "Tentaram apagar cada vestígio daquela grande queda.",
            "visual_prompt": f"Shadowy figures sealing ancient scrolls inside a subterranean vault with golden chains, {short_topic}, neo-noir lighting, 9:16",
        },
        {
            "narration": "Porém nenhuma chama se apaga na escuridão.",
            "visual_prompt": f"A single brilliant golden flame igniting in pitch black darkness, illuminating ancient armor, {short_topic}, macro shot, 9:16",
        },
        {
            "narration": "A segunda profecia começou a se cumprir.",
            "visual_prompt": f"Colossal stone statues awakening with glowing runes along a canyon, {short_topic}, wide low-angle cinematic shot, 9:16",
        },
        {
            "narration": "O choque entre luz e trevas chegou.",
            "visual_prompt": f"Radiant spear of light piercing through a massive shadow colossus, {short_topic}, epic dark anime battle, 9:16",
        },
        {
            "narration": "Nas cinzas, a peça final foi encontrada.",
            "visual_prompt": f"Hand wearing gauntlets picking up a shattered glowing crystal relic on ashes, {short_topic}, extreme close-up, 9:16",
        },
        {
            "narration": "Cada fragmento servia a um único propósito.",
            "visual_prompt": f"Astral tree of light connecting heaven and the dark underworld, {short_topic}, breathtaking vertical composition, 9:16",
        },
        {
            "narration": "No instante decisivo, a verdade veio à tona.",
            "visual_prompt": f"Archangel spreading six luminous wings amidst a storm of golden sparks, {short_topic}, climax shot, 8k dark anime, 9:16",
        },
        {
            "narration": "O trono antigo desmoronou diante do juízo.",
            "visual_prompt": f"Crumbling dark marble pillars and falling crowns in slow motion with fire embers, {short_topic}, dramatic lighting, 9:16",
        },
        {
            "narration": "Seu eco ainda molda o mundo atual.",
            "visual_prompt": f"Modern dark skyline reflected in an ancient mystical mirror with glowing symbols, {short_topic}, cinematic contrast, 9:16",
        },
        {
            "narration": "Agora você enxerga os sinais ocultos.",
            "visual_prompt": f"Mysterious figure turning back with glowing eyes in volumetric blue fog, {short_topic}, hypnotic gaze, 9:16",
        },
        {
            "narration": "Pois o último capítulo acaba de recomeçar.",
            "visual_prompt": f"Silhouette of the celestial winged figure returning to the cosmic rift, seamless loop visual, {short_topic}, dark anime, 9:16",
        },
    ]


def _build_story_visual_bible(
    title: str,
    full_narration: str = "",
    existing_bible: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Constrói ou normaliza a "Bíblia Visual da História" (Story Visual Bible) compartilhada
    pelas 20 cenas do vídeo, garantindo que TODAS as imagens retratem exatamente o MESMO
    personagem principal, o MESMO universo/cenário, a MESMA paleta de cores e o MESMO traço.
    """
    existing = dict(existing_bible or {})
    combined_text = f"{title} {full_narration}".lower()

    # Detecta arquétipo temático da história para definir feições físicas imutáveis caso não venham prontas
    is_celestial_or_biblical = any(
        k in combined_text
        for k in (
            "anjo", "arcanjo", "lúcifer", "lucifer", "céu", "celestial", "deus", "altíssimo",
            "estrela da manhã", "rebelião", "querubim", "serafim", "trono", "profecia", "bíblic",
        )
    )

    if is_celestial_or_biblical:
        default_protagonist = (
            "tall male celestial archangel Lucifer with long flowing platinum-silver hair, sharp glowing golden amber eyes, "
            "clean-shaven sculpted face, ornate black-and-gold celestial armor and large dark-golden feathered wings"
        )
        default_world = (
            "ancient gothic celestial sanctuary of dark obsidian and golden marble pillars "
            "floating amidst cosmic storm clouds"
        )
        default_palette = "deep obsidian black, radiant molten gold, and cold astral sapphire blue"
    else:
        default_protagonist = (
            "charismatic male protagonist with sharp intense amber eyes, medium-length dark tousled hair, "
            "angular jawline, wearing a long dark high-collar trench cloak with subtle golden trim"
        )
        default_world = (
            "ancient monumental gothic citadel and subterranean sanctuary shrouded in volumetric mist "
            "and dramatic shafts of golden light"
        )
        default_palette = "deep midnight indigo, obsidian black, warm amber gold, and cold cyan rim lighting"

    default_style = (
        "2D dark epic anime cinematic illustration in the style of Castlevania Nocturne, "
        "dramatic chiaroscuro volumetric lighting, single unified composition"
    )

    protagonist = (existing.get("protagonist_description") or existing.get("character_anchor") or "").strip()
    world_setting = (existing.get("world_setting") or existing.get("world_anchor") or "").strip()
    color_palette = (existing.get("color_palette") or "").strip()
    art_style = (existing.get("art_style") or existing.get("style_anchor") or "").strip()

    # Remove expressões que induzem divisão de tela ("character design sheet", "split screen")
    art_style = re.sub(r"\b(?:consistent\s+)?character\s+design\s+sheet\b", "single unified frame", art_style, flags=re.IGNORECASE)

    return {
        "protagonist_description": protagonist if len(protagonist) >= 25 else default_protagonist,
        "world_setting": world_setting if len(world_setting) >= 20 else default_world,
        "color_palette": color_palette if len(color_palette) >= 12 else default_palette,
        "art_style": art_style if len(art_style) >= 20 else default_style,
    }


def _enforce_visual_continuity_across_scenes(
    scenes: List[Dict[str, Any]],
    visual_bible: Dict[str, str],
    title: str = "Vídeo Dark",
) -> List[Dict[str, Any]]:
    """
    Compilador de Continuidade Visual Cena-a-Cena:
    Garante que todas as 20 cenas pareçam frames consecutivos da MESMA história e com o MESMO
    protagonista, colocando a ação dramática e o ângulo de câmera da cena em primeiro plano
    seguidos pela descrição concisa do protagonista e do cenário (cabendo nos 77 tokens do CLIP).
    """
    protagonist = visual_bible["protagonist_description"]
    world_setting = visual_bible["world_setting"]
    color_palette = visual_bible["color_palette"]
    art_style = visual_bible["art_style"]

    act_progression = [
        # Ato I (Cenas 1 a 6): Apresentação majestosa no mesmo santuário
        "Act I wide establishing shot, standing majestically in luminous celestial hall",
        "Act I medium shot from side angle, golden gemstones gleaming on his ornate chest armor under divine light",
        "Act I dynamic medium shot, harmonic golden light waves radiating from his outstretched hand",
        "Act I wide tracking shot from behind, walking across sacred obsidian floor toward the altar of fire",
        "Act I dramatic close-up on his face and glowing golden eyes, subtle shadow of ambition crossing his expression",
        "Act I low-angle heroic shot, his massive wings spread wide casting a long dark shadow across marble pillars",
        # Ato II (Cenas 7 a 15): Transformação da expressão e tensão crescente no mesmo universo
        "Act II intense close-up on his hands and torso, sacred golden aura twisting into dark crimson-gold sparks",
        "Act II cinematic over-the-shoulder shot, whispering shadows echoing between towering gothic columns",
        "Act II low-angle dramatic shot, looking up toward the highest celestial throne with defiant gaze",
        "Act II side profile portrait, dark golden energy veins glowing across his ornate armor",
        "Act II wide council scene, standing on a raised dais addressing winged celestial figures in shadow",
        "Act II dynamic wide angle, a glowing rift of golden-violet light cracking the celestial dome behind him",
        "Act II tense confrontation shot, armored celestial guardians watching him from the upper colonnade",
        "Act II epic wide shot, legions of winged silhouettes aligning behind him under falling golden stars",
        "Act II dramatic storm action shot, lightning and cosmic shockwaves shattering the sanctuary around his raised hand",
        # Ato III (Cenas 16 a 20): Clímax e resolução mantendo 100% do mesmo personagem e cenário
        "Act III extreme close-up on his fierce glowing eyes and silver hair in the storm wind",
        "Act III grand battle action shot, clashing beams of golden light and dark abyssal fire in the sanctuary",
        "Act III dramatic three-quarter shot, standing amidst fractured marble pillars and swirling golden embers",
        "Act III atmospheric wide shot from behind, gazing over the divided celestial horizon with wings spread",
        "Act III final cinematic loop shot, turning his head back over his shoulder with glowing golden eyes in cosmic mist",
    ]

    compiled_scenes: List[Dict[str, Any]] = []
    for idx, sc in enumerate(scenes):
        act_hint = act_progression[idx % len(act_progression)]
        raw_vis = (sc.get("visual_prompt") or "").strip()
        raw_narr = clean_narration_for_tts(sc.get("narration") or "")

        # Limpa sufixos redundantes para re-ancorar na estrutura unificada da história
        cleaned_action = re.sub(
            r"\b(?:vertical\s*9:16|9:16|8k\s*resolution|8k|unreal\s*engine\s*5|character\s+design\s+sheet)\b",
            "",
            raw_vis,
            flags=re.IGNORECASE,
        ).strip(" ,.-")

        if not cleaned_action or len(cleaned_action) < 35:
            scene_action = f"{act_hint}, depicting '{raw_narr}'"
        else:
            scene_action = f"{act_hint}, {cleaned_action}"

        # Coloca a ação específica e o ângulo de câmera no início para evitar poses estáticas repetidas,
        # mantendo o mesmo protagonista, cenário e paleta em todas as 20 cenas:
        continuous_prompt = (
            f"Scene {idx + 1:02d} action: {scene_action}. "
            f"Same main character ({protagonist}) in {world_setting}. "
            f"{art_style}, {color_palette}, vertical 9:16"
        )

        updated_sc = dict(sc)
        updated_sc["visual_prompt"] = continuous_prompt
        updated_sc["visual_bible"] = visual_bible
        compiled_scenes.append(updated_sc)

    return compiled_scenes


async def _generate_twenty_scenes_via_gemini(
    title: str,
    context_text: str,
    api_key: str,
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, str]]]:
    """
    Solicita ao Gemini a criação da Bíblia Visual da História (`visual_bible`) e de exatamente
    20 cenas conectadas em narrativa contínua de 60 segundos, garantindo que o mesmo personagem
    e o mesmo universo visual sejam mantidos da Cena 1 à Cena 20.
    """
    if not api_key or os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") == "1":
        return [], None

    try:
        from src.services.jeffrey_orchestrator import call_gemini_generate_content

        sys_prompt = """Você é o Diretor de Roteiro e Fotografia de Canal Dark do ABVOS.
Gere uma Bíblia Visual Unificada (`visual_bible`) e EXATAMENTE 20 cenas sequenciais e contínuas para um vídeo vertical de 60 segundos.
Regras obrigatórias de Continuidade Visual e Narrativa:
1. A narração (`narration`) das 20 cenas deve formar UMA ÚNICA HISTÓRIA CONTÍNUA, envolvente e cronológica em Português do Brasil.
2. Cada `narration` deve ter entre 7 e 10 palavras (para durar cerca de 3 segundos na fala).
3. PROIBIDO incluir `[pausa]`, colchetes, `(fase 2)`, parênteses de direção, ou prefixos como `Cena 1:` dentro de `narration`.
4. CONTINUIDADE TOTAL DE PERSONAGEM E HISTÓRIA: Defina em `visual_bible` a aparência física EXATA e IMUTÁVEL do protagonista (`protagonist_description`: gênero, rosto, cor e corte de cabelo, cor dos olhos, armadura/vestimenta), o cenário principal (`world_setting`), a paleta de cores (`color_palette`) e o estilo (`art_style`).
5. Em CADA UM dos 20 `visual_prompt` (em INGLÊS), repita as características físicas do protagonista de `visual_bible` e descreva uma cena física e concreta (postura, expressão facial, ação visível e iluminação no mesmo cenário). NUNCA escreva prompts abstratos ou mude o personagem de uma cena para outra.

Responda APENAS um JSON válido no formato:
{
  "visual_bible": {
    "protagonist_description": "tall male celestial archangel with long flowing platinum-silver hair, sharp glowing golden amber eyes, sculpted face, wearing ornate black-and-gold celestial armor and six dark-golden feathered wings",
    "world_setting": "ancient monumental gothic celestial sanctuary of dark obsidian and golden marble pillars",
    "color_palette": "deep obsidian black, radiant molten gold, and cold astral sapphire blue",
    "art_style": "dark epic anime cinematic painting in the style of Castlevania and Fate/Zero, consistent character sheet"
  },
  "scenes": [
    {
      "scene_number": 1,
      "narration": "Frase falada limpa em português com sete a dez palavras.",
      "visual_prompt": "Same tall male celestial archangel with long platinum-silver hair, golden eyes and black-and-gold armor standing in the gothic celestial sanctuary, dramatic volumetric lighting, 9:16",
      "on_screen_text": "TÍTULO CURTO"
    }
  ]
}"""

        user_msg = f"Título do Vídeo: {title}\nContexto / Tema: {clean_narration_for_tts(context_text) or title}\nGere a visual_bible e as 20 cenas contínuas agora."
        resp_data, _ = await call_gemini_generate_content(
            api_key=api_key,
            contents=[{"role": "user", "parts": [{"text": user_msg}]}],
            system_instruction=sys_prompt,
            tools_declarations=[],
            preferred_model="gemini-3.8-flash",
        )
        candidates = resp_data.get("candidates", [])
        if candidates:
            raw = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            parsed = json.loads(raw)
            sc_list = parsed.get("scenes") or parsed.get("items") or []
            v_bible = parsed.get("visual_bible") if isinstance(parsed.get("visual_bible"), dict) else None
            if isinstance(sc_list, list) and len(sc_list) >= 10:
                return sc_list, v_bible
    except Exception as e:
        logger.warning(f"Não foi possível gerar 20 cenas via Gemini complementar: {e}")

    return [], None


def ensure_twenty_scenes(
    scenes: Optional[List[Dict[str, Any]]],
    full_narration: str,
    title: str = "Vídeo Dark",
    visual_bible: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """
    Garante obrigatoriamente 20 cenas conectadas na mesma história (totalizando 60 segundos),
    com narração contínua, limpa (sem '[pausa]', sem '(fase 2)', sem logs de status) e com
    continuidade visual estrita (mesmo protagonista, mesmo cenário, mesma paleta de cores):
    - Part 1: Cenas 01 a 06 (0s a 18s) - Hook Hipnótico e Apresentação do Protagonista/Mundo
    - Part 2: Cenas 07 a 15 (18s a 45s) - Desenvolvimento e Tensão Narrativa no Mesmo Universo
    - Part 3: Cenas 16 a 20 (45s a 60s) - Clímax, Revelação e Looping Contínuo
    """
    camera_styles = [
        "Dynamic macro push-in, anamorphic lens, volumetric dark fog",
        "Wide cinematic angle, ominous shadows, dark anime masterpiece",
        "Extreme close up on character face and eyes, dramatic chiaroscuro side lighting",
        "Slow atmospheric dolly in, cold blue and gold rim light, 8k resolution",
        "Low-angle heroic shot in deep darkness, glowing embers and particles",
        "High-contrast dramatic composition, epic fantasy lighting, 8k",
    ]

    fallback_beats = _build_narrative_beats(title)
    clean_full = clean_narration_for_tts(full_narration)
    story_bible = _build_story_visual_bible(title=title, full_narration=clean_full, existing_bible=visual_bible)

    # Extrai sentenças reais da narração caso existam
    narration_sentences: List[str] = []
    if clean_full:
        raw_parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", clean_full) if len(p.strip()) > 4]
        for part in raw_parts:
            words = part.split()
            if len(words) > 14:
                # Divide frases muito longas em segmentos de ~8-10 palavras para caber em 3s
                for k in range(0, len(words), 9):
                    seg = " ".join(words[k:k + 9]).strip()
                    if seg:
                        narration_sentences.append(seg)
            else:
                narration_sentences.append(part)

    input_scenes = list(scenes or [])
    normalized_scenes: List[Dict[str, Any]] = []

    if len(input_scenes) >= 20:
        for i in range(20):
            sc = input_scenes[i]
            raw_narr = sc.get("narration") or sc.get("script") or ""
            clean_narr = clean_narration_for_tts(raw_narr) or fallback_beats[i]["narration"]
            v_prompt = (sc.get("visual_prompt") or "").strip()
            if not v_prompt or len(v_prompt) < 12:
                v_prompt = f"Dark epic anime illustration depicting: {clean_narr}, {camera_styles[i % len(camera_styles)]}, vertical 9:16"
            normalized_scenes.append({
                "scene_number": i + 1,
                "duration": 3.0,
                "narration": clean_narr,
                "visual_prompt": v_prompt,
                "on_screen_text": sc.get("on_screen_text") or sc.get("title") or f"CENA {i + 1:02d}",
            })
        return _enforce_visual_continuity_across_scenes(normalized_scenes, story_bible, title=title)

    # Se vieram menos de 20 cenas, coleta as cenas válidas e completa com as sentenças/beats contínuos
    collected_items: List[Dict[str, str]] = []
    for sc in input_scenes:
        c_narr = clean_narration_for_tts(sc.get("narration") or sc.get("script") or "")
        c_vis = (sc.get("visual_prompt") or "").strip()
        if c_narr:
            # Se a narração de um item for um parágrafo longo, divide em cenas de ~9 palavras
            words = c_narr.split()
            if len(words) > 15:
                chunks = [" ".join(words[k:k + 9]) for k in range(0, len(words), 9)]
                for sub_idx, ch in enumerate(chunks):
                    cam = camera_styles[(len(collected_items) + sub_idx) % len(camera_styles)]
                    collected_items.append({
                        "narration": ch,
                        "visual_prompt": f"{c_vis}, shot variation #{sub_idx + 1} depicting '{ch}', {cam}, 9:16" if c_vis else f"Dark epic anime scene depicting: {ch}, {cam}, 9:16",
                        "on_screen_text": sc.get("on_screen_text") or sc.get("title") or "",
                    })
            else:
                collected_items.append({
                    "narration": c_narr,
                    "visual_prompt": c_vis,
                    "on_screen_text": sc.get("on_screen_text") or sc.get("title") or "",
                })

    # Se ainda houver frases em narration_sentences não usadas, adiciona na sequência
    used_texts = {it["narration"].lower() for it in collected_items}
    for sent in narration_sentences:
        if len(collected_items) >= 20:
            break
        if sent.lower() not in used_texts:
            collected_items.append({
                "narration": sent,
                "visual_prompt": "",
                "on_screen_text": "",
            })
            used_texts.add(sent.lower())

    for i in range(20):
        cam = camera_styles[i % len(camera_styles)]
        beat = fallback_beats[i]
        if i < len(collected_items):
            narr_text = collected_items[i]["narration"]
            vis_prompt = collected_items[i]["visual_prompt"]
            on_screen = collected_items[i]["on_screen_text"] or f"CENA {i + 1:02d}"
        else:
            narr_text = beat["narration"]
            vis_prompt = beat["visual_prompt"]
            on_screen = f"CENA {i + 1:02d}"

        if not vis_prompt or len(vis_prompt) < 15:
            vis_prompt = (
                f"Dark epic anime and cinematic fantasy illustration depicting: {narr_text} "
                f"(theme: {clean_narration_for_tts(title) or title}), {cam}, volumetric lighting, 8k, vertical 9:16"
            )
        else:
            vis_prompt = f"{vis_prompt}, {cam}, vertical 9:16"

        normalized_scenes.append({
            "scene_number": i + 1,
            "duration": 3.0,
            "narration": narr_text,
            "visual_prompt": vis_prompt,
            "on_screen_text": on_screen,
        })

    return _enforce_visual_continuity_across_scenes(normalized_scenes, story_bible, title=title)


@router.task(job_timeout=None)
async def execute_full_video_pipeline(
    task_id: int,
    business_id: int,
    scenes: Optional[List[Dict[str, Any]]] = None,
    full_narration: Optional[str] = None,
    voice_persona: Optional[str] = None,
    gemini_key: Optional[str] = None,
    elevenlabs_key: Optional[str] = None,
    visual_bible: Optional[Dict[str, str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Motor Principal de Renderização Multimídia Autônoma ABVOS (Vídeo 9:16, 1080x1920):
    1. job_timeout=None (Timeout Infinite): Sem limite de tempo no ARQ/Redis/FastAPI.
    2. Continuidade Visual Garantida (Story Visual Bible + mesmo protagonista + mesmo motor Flux + story_seed).
    3. Execução Sequencial Garantida (20 Cenas sincronizadas com a voz = exatamente 60s / 1 minuto).
    4. Síntese de voz neural limpa e sincronização palavra por palavra (WordBoundary) em 30fps nas legendas .ass/.srt.
    5. Compilação final via FFmpeg de exatamente 1 minuto de duração.
    """
    task_media_dir = get_task_media_dir(business_id, task_id)
    task_output_dir = get_task_output_dir(business_id, task_id)
    scenes_dir = task_media_dir / "scenes"
    audio_path = str(task_media_dir / "narration.mp3")
    srt_path = str(task_media_dir / "subtitles.srt")
    ass_path = str(task_media_dir / "subtitles.ass")
    final_video_path = str(task_media_dir / f"video_dark_task_{task_id}.mp4")

    logger.info(f"== [ABVOS VIDEO WORKER] INICIANDO PIPELINE (TASK #{task_id}, BIZ #{business_id}) ==")
    await _persist_video_progress(
        task_id=task_id,
        business_id=business_id,
        current_scene=0,
        total_scenes=20,
        stage="prompts",
        percent=0.0,
    )

    task_title = f"Task #{task_id}"
    if not full_narration or not scenes or not gemini_key:
        try:
            from src.database import AsyncSessionLocal
            from src.models import Task, User
            from sqlalchemy.future import select
            from sqlalchemy.orm import selectinload

            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    select(Task).options(selectinload(Task.business)).where(Task.id == task_id)
                )
                db_task = res.scalar_one_or_none()
                if db_task:
                    task_title = db_task.title
                    if not full_narration:
                        full_narration = clean_narration_for_tts(db_task.description or "") or db_task.title
                    if not gemini_key:
                        try:
                            from src.services.jeffrey_orchestrator import get_effective_gemini_key
                            u_res = await session.execute(select(User).where(User.id == db_task.user_id))
                            db_user = u_res.scalar_one_or_none()
                            if db_user:
                                gemini_key = await get_effective_gemini_key(db_user, session)
                        except Exception:
                            pass
        except Exception as load_err:
            logger.warning(f"Não foi possível carregar dados complementares do banco: {load_err}")

    # Se a task veio com poucas cenas (ex: disparada direto do Kanban/Series), gera as 20 cenas conectadas via Gemini
    if (not scenes or len(scenes) < 10) and gemini_key and os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") != "1":
        gemini_scenes, gemini_bible = await _generate_twenty_scenes_via_gemini(
            title=task_title,
            context_text=full_narration or task_title,
            api_key=gemini_key,
        )
        if gemini_scenes:
            scenes = gemini_scenes
        if gemini_bible and not visual_bible:
            visual_bible = gemini_bible

    # PASSO 1: Normalização Garantida de 20 Cenas com Bíblia Visual da História (mesmo personagem e cenário)
    story_bible = _build_story_visual_bible(
        title=task_title,
        full_narration=full_narration or task_title,
        existing_bible=visual_bible,
    )
    twenty_scenes = ensure_twenty_scenes(
        scenes,
        full_narration or task_title,
        title=task_title,
        visual_bible=story_bible,
    )
    total_scenes_count = len(twenty_scenes)
    assert total_scenes_count == 20, f"O pipeline exige exatamente 20 cenas, obtido {total_scenes_count}"

    # PASSO 2: Execução Sequencial das 20 Cenas com Progresso em Tempo Real e Seed Fixa da História
    logger.info("[Passo 1/4] Gerando ilustrações contínuas das 20 cenas (Mesmo Protagonista e Universo)...")

    async def _on_scene_progress(current_sc: int, total_sc: int):
        sc_pct = round((current_sc / max(1, total_sc)) * 48.0, 1)
        if current_sc == 5:
            sc_pct = 25.0
        await _persist_video_progress(
            task_id=task_id,
            business_id=business_id,
            current_scene=current_sc,
            total_scenes=total_sc,
            stage="images",
            percent=sc_pct,
        )

    story_seed = 100000 + ((int(task_id or 1) * 7919) % 800000)
    image_paths = await generate_all_scene_images(
        scenes=twenty_scenes,
        output_dir=scenes_dir,
        gemini_key=gemini_key,
        progress_callback=_on_scene_progress,
        sequential=True,
        visual_bible=story_bible,
        story_seed=story_seed,
    )

    # PASSO 3: Síntese de Narração de Áudio (TTS) Unificada e Limpa
    logger.info("[Passo 2/4] Sintetizando narração em áudio para o vídeo...")
    await _persist_video_progress(
        task_id=task_id,
        business_id=business_id,
        current_scene=10,
        total_scenes=20,
        stage="tts",
        percent=50.0,
    )
    # Constrói o texto falado diretamente da sequência limpa das 20 cenas para 100% de fidelidade áudio <-> legenda <-> imagem
    scene_narrations = [clean_narration_for_tts(sc.get("narration", "")) for sc in twenty_scenes]
    scene_narrations = [s if s.endswith((".", "!", "?")) else f"{s}." for s in scene_narrations if s]
    audio_text = " ".join(scene_narrations) or clean_narration_for_tts(full_narration or task_title)

    tts_result = await synthesize_narration(
        text=audio_text,
        output_path=audio_path,
        elevenlabs_key=elevenlabs_key,
        preferred_voice=voice_persona,
    )
    total_audio_duration = tts_result["duration_seconds"]
    word_timings = tts_result.get("word_timings") or []

    # PASSO 4: Sincronização Cena <-> Fala e Geração de Legendas Dinâmicas (sem misturar frases)
    logger.info(f"[Passo 3/4] Gerando legendas dinâmicas sincronizadas ({len(word_timings)} palavras mapeadas)...")
    scenes_timing = compute_scene_timings_from_words(
        scenes=twenty_scenes,
        word_timings=word_timings,
        target_total_duration=60.0,
    )
    scene_durations = [float(st.get("duration", 3.0)) for st in scenes_timing]

    subtitles_result = generate_subtitles(
        scenes_timing=scenes_timing,
        output_srt_path=srt_path,
        output_ass_path=ass_path,
        word_timings=word_timings,
    )

    # PASSO 5: Confirmação Estrita dos Assets Antes de Disparar FFmpeg
    logger.info("[Passo 4/4] Validando integridade física dos assets antes da compilação FFmpeg...")
    verified_images: List[str] = []
    for i in range(1, 21):
        sc_file = scenes_dir / f"scene_{i:02d}.jpg"
        if not sc_file.exists() or sc_file.stat().st_size == 0:
            logger.warning(f"Asset da cena #{i} ausente no disco. Gerando imagem de segurança.")
            sc_meta = twenty_scenes[i - 1] if i - 1 < len(twenty_scenes) else {}
            fallback = create_cinematic_dark_backdrop(
                width=1080,
                height=1920,
                scene_number=i,
                title=sc_meta.get("on_screen_text") or f"Cena {i}",
                prompt=sc_meta.get("visual_prompt") or "",
            )
            fallback.save(str(sc_file), "JPEG", quality=92)
        verified_images.append(str(sc_file))

    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise FileNotFoundError(f"Asset de áudio {audio_path} não foi confirmado no disco antes do FFmpeg.")

    assert len(verified_images) == 20, f"Confirmação falhou: esperado 20 assets de imagem, encontrado {len(verified_images)}"

    # ETAPA 4: Renderizando vídeo via FFmpeg... (80%)
    await _persist_video_progress(
        task_id=task_id,
        business_id=business_id,
        current_scene=20,
        total_scenes=20,
        stage="ffmpeg",
        percent=80.0,
    )

    # PASSO 6: Compilação Final via FFmpeg (Exatamente 1 minuto / 60 segundos de duração a 30fps)
    render_result = await render_video_with_audio_and_subtitles(
        image_paths=verified_images,
        audio_path=audio_path,
        output_video_path=final_video_path,
        subtitle_ass_path=ass_path,
        fps=30,
        width=1080,
        height=1920,
        scene_duration=3.0,
        scene_durations=scene_durations,
    )

    # Sincroniza e garante os artefatos finais no diretório de saída oficial /app/storage/output
    output_video_file = task_output_dir / f"video_dark_task_{task_id}.mp4"
    output_audio_file = task_output_dir / "narration.mp3"
    output_srt_file = task_output_dir / "subtitles.srt"
    output_scenes_dir = task_output_dir / "scenes"
    output_scenes_dir.mkdir(parents=True, exist_ok=True)

    try:
        if os.path.exists(final_video_path):
            shutil.copy2(final_video_path, str(output_video_file))
        if os.path.exists(audio_path):
            shutil.copy2(audio_path, str(output_audio_file))
        if os.path.exists(srt_path):
            shutil.copy2(srt_path, str(output_srt_file))
        for v_img in verified_images:
            if os.path.exists(v_img):
                shutil.copy2(v_img, str(output_scenes_dir / Path(v_img).name))
    except Exception as copy_err:
        logger.warning(f"Aviso ao copiar arquivos para /app/storage/output: {copy_err}")

    # ETAPA 5: Concluído. Arquivo salvo em /app/storage/output/ (100%)
    await _persist_video_progress(
        task_id=task_id,
        business_id=business_id,
        current_scene=20,
        total_scenes=20,
        stage="done",
        percent=100.0,
        is_completed=True,
        output_path="/app/storage/output/",
    )

    video_relative_url = f"/outputs/biz_{business_id}/task_{task_id}/video_dark_task_{task_id}.mp4"
    audio_relative_url = f"/outputs/biz_{business_id}/task_{task_id}/narration.mp3"
    srt_relative_url = f"/outputs/biz_{business_id}/task_{task_id}/subtitles.srt"

    result_manifest = {
        "success": True,
        "business_id": business_id,
        "task_id": task_id,
        "scenes_count": 20,
        "scenes": twenty_scenes,
        "visual_bible": story_bible,
        "video": {
            "path": final_video_path,
            "url": video_relative_url,
            "resolution": render_result.get("resolution", "1080x1920"),
            "aspect_ratio": "9:16",
            "duration_seconds": round(sum(scene_durations), 2) if scene_durations else 60.0,
            "size_mb": render_result.get("size_mb", 0.0),
        },
        "audio": {
            "path": audio_path,
            "url": audio_relative_url,
            "duration_seconds": total_audio_duration,
            "provider": tts_result.get("provider", "edge_tts"),
        },
        "subtitles": {
            "srt_path": srt_path,
            "srt_url": srt_relative_url,
            "ass_path": ass_path,
        },
        "images_generated": [
            f"/api/media/file/biz_{business_id}/task_{task_id}/scenes/{Path(p).name}"
            for p in verified_images
        ],
    }

    logger.info(f"== PIPELINE MULTIMÍDIA CONCLUÍDO COM SUCESSO! Vídeo 60s: {final_video_path} ==")
    return result_manifest


# Alias para retrocompatibilidade
execute_full_media_pipeline = execute_full_video_pipeline
