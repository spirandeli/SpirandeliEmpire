import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from src.services.media.agents.base import AgentContext, BaseMediaAgent
from src.services.media.agents.contracts import (
    AgentStage,
    PipelineManifest,
    ScriptArtifact,
    ScriptSceneSpec,
    VisualBibleSpec,
)
from src.services.media.tts_service import clean_narration_for_tts

logger = logging.getLogger("abvos.media.agents.script")

VALID_MOTIONS = ("zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up")


def _build_adaptive_visual_bible(
    title: str,
    topic: str,
    niche: str,
    requested_style: str = "",
    raw_bible: Optional[Dict[str, Any]] = None,
) -> VisualBibleSpec:
    """
    Constrói uma Bíblia Visual adaptativa ao tema e nicho reais da pauta,
    sem forçar estética de anime sombrio quando o tema for realista, histórico ou corporativo.
    """
    raw = dict(raw_bible or {})
    combined = f"{title} {topic} {niche} {requested_style}".lower()

    is_anime_or_fantasy = any(
        k in combined
        for k in ("anime", "castlevania", "anjo", "arcanjo", "lúcifer", "lucifer", "mitologia", "fantasia", "demônio")
    )
    is_tech_or_business = any(
        k in combined
        for k in ("ia", "ai", "tecnologia", "negócio", "finança", "dinheiro", "saas", "startup", "marketing", "mercado")
    )

    if requested_style and len(requested_style.strip()) >= 12:
        default_style = requested_style.strip()
    elif is_anime_or_fantasy:
        default_style = "2D dark epic anime cinematic illustration, dramatic chiaroscuro volumetric lighting, crisp linework"
    elif is_tech_or_business:
        default_style = "Sleek neo-noir documentary cinematography, 35mm anamorphic film still, sharp architectural depth"
    else:
        default_style = "Atmospheric cinematic documentary film still, realistic dramatic lighting, rich environmental texture"

    if is_anime_or_fantasy:
        default_protagonist = (
            "striking central figure with expressive luminous eyes, weathered dark cloak with subtle metallic embroidery, "
            "dynamic silhouette integrated naturally into the environment"
        )
        default_world = (
            "monumental ancient stone architecture, towering arches, deep atmospheric mist and warm rim light rays"
        )
        default_palette = "obsidian black, molten gold, and cold astral sapphire blue"
    elif is_tech_or_business:
        default_protagonist = (
            "focused strategist in sharp minimalist dark tailored coat, subtle rim light on profile, interacting with environment"
        )
        default_world = (
            "rain-slicked modern metropolis skyline, glass command rooms, glowing data reflections and deep shadows"
        )
        default_palette = "deep slate charcoal, electric cyan, and warm amber highlights"
    else:
        default_protagonist = (
            "observant investigator wearing a textured dark coat, expressive face lit by directional natural side light"
        )
        default_world = (
            "authentic atmospheric locations with layered foregrounds, misty depth, historic architecture and dramatic skies"
        )
        default_palette = "deep midnight navy, warm tungsten amber, and muted slate silver"

    protagonist = str(raw.get("protagonist_description") or "").strip()
    world = str(raw.get("world_setting") or "").strip()
    palette = str(raw.get("color_palette") or "").strip()
    style = str(raw.get("art_style") or "").strip()
    lighting = str(raw.get("lighting_mood") or "").strip()
    negatives = str(raw.get("negative_constraints") or "").strip()

    return VisualBibleSpec(
        protagonist_description=protagonist if len(protagonist) >= 20 else default_protagonist,
        world_setting=world if len(world) >= 20 else default_world,
        color_palette=palette if len(palette) >= 10 else default_palette,
        art_style=style if len(style) >= 12 else default_style,
        lighting_mood=lighting if len(lighting) >= 8 else "cinematic volumetric contrast lighting",
        negative_constraints=negatives or "no watermark, no text overlay, no split screen, no distorted faces",
    )


def _build_structured_fallback_scenes(title: str, topic: str, format_type: str) -> List[Dict[str, Any]]:
    """Fallback estruturado limpo e coerente com o tema (usado apenas offline ou sem chave Gemini)."""
    subject = clean_narration_for_tts(topic or title) or "esse fenômeno oculto"
    short_subj = " ".join(subject.split()[:5])
    beats = [
        ("hook", f"Quase ninguém percebeu o que mudou em {short_subj}.", "Wide establishing shot revealing vast atmospheric setting at dusk, rule of thirds, 9:16", False, "zoom_in"),
        ("hook", "Mas um detalhe silencioso revelou toda a verdade.", "Macro detail shot of mysterious clue resting on weathered surface under directional light, 9:16", False, "zoom_out"),
        ("setup", "Por anos, os registros oficiais contaram outra versão.", "Medium shot of dimly lit archive room with towering shelves and dust motes in sunbeams, 9:16", True, "pan_right"),
        ("setup", "Poucas pessoas tiveram acesso aos documentos originais.", "Over-the-shoulder shot of figure examining aged pages by warm desk lamp, deep background, 9:16", True, "zoom_in"),
        ("setup", "Quando os dados foram cruzados, o padrão surgiu.", "Close detail of interconnected notes and glowing lines across a dark table, 9:16", False, "pan_left"),
        ("development", "Nada naquela sequência havia acontecido por acaso.", "Low-angle architectural shot looking up through tall shadowed pillars into stormy sky, 9:16", False, "tilt_up"),
        ("development", "Cada decisão anterior apontava para o mesmo objetivo.", "Medium wide shot of lone figure walking along misty corridor with dramatic side lighting, 9:16", True, "pan_right"),
        ("development", "Nos bastidores, o verdadeiro custo já era cobrado.", "Atmospheric wide shot of shadowed hall illuminated by amber reflections on wet floor, 9:16", False, "zoom_in"),
        ("development", "Quem tentou alertar o público acabou sendo ignorado.", "Three-quarter shot of figure standing off-center beside tall frosted window looking outward, 9:16", True, "zoom_out"),
        ("development", "O ponto de virada aconteceu longe dos holofotes.", "Cinematic high-angle view of isolated compound surrounded by drifting evening fog, 9:16", False, "pan_left"),
        ("tension", "Em poucas horas, toda a estrutura começou a ruir.", "Dynamic wide shot with dramatic chiaroscuro clouds breaking over historic skyline, 9:16", False, "zoom_in"),
        ("tension", "As peças ocultas finalmente se encaixaram diante deles.", "Detailed shot of mechanical dial or key locking into place with golden rim light, 9:16", False, "zoom_out"),
        ("tension", "O que parecia um erro era um plano antigo.", "Medium shot of protagonist on left third facing vast illuminated wall of maps, 9:16", True, "pan_right"),
        ("climax", "E o impacto dessa descoberta atravessou décadas inteiras.", "Epic wide shot bridging past ruins with modern horizon under dramatic twilight, 9:16", False, "tilt_up"),
        ("climax", "Hoje, os mesmos sinais aparecem diante de nós.", "Cinematic street-level wide view at night with glowing reflections and lone silhouette, 9:16", True, "zoom_in"),
        ("cta", "Agora que você conhece a origem, observe ao redor.", "Atmospheric closing shot looking toward distant illuminated horizon through mist, seamless loop, 9:16", True, "zoom_out"),
    ]
    if format_type == "long":
        beats = beats[:12]

    result = []
    for idx, (act, narr, vis, inc_char, motion) in enumerate(beats, start=1):
        words_n = max(1, len(narr.split()))
        result.append({
            "scene_number": idx,
            "act": act,
            "narration": narr,
            "visual_prompt_en": vis,
            "include_character": inc_char,
            "camera_angle": vis.split(",")[0].strip(),
            "camera_motion": motion,
            "estimated_seconds": round(max(2.2, words_n / 2.45), 2),
            "on_screen_text": f"CENA {idx:02d}",
        })
    return result


def validate_and_polish_script(artifact: ScriptArtifact) -> ScriptArtifact:
    """
    Validador e polidor determinístico do Agente de Roteiros:
    - Limpa qualquer marcação técnica ou prefixo de cena das falas;
    - Garante pontuação final adequada para respiração natural do TTS;
    - Calcula contagem de palavras e duração estimada em ritmo natural (2.4 palavras/s);
    - Garante variação de movimentos de câmera para o Montador.
    """
    notes: List[str] = []
    cleaned_scenes: List[ScriptSceneSpec] = []
    total_words = 0
    total_secs = 0.0

    for idx, sc in enumerate(artifact.scenes, start=1):
        raw_narr = sc.narration or ""
        clean_narr = clean_narration_for_tts(raw_narr)
        if clean_narr != raw_narr.strip():
            notes.append(f"Cena {idx:02d}: removidos marcadores técnicos da narração.")
        if clean_narr and clean_narr[-1] not in ".!?…":
            clean_narr = f"{clean_narr}."

        w_count = len(clean_narr.split())
        total_words += w_count
        est_sec = round(max(2.0, w_count / 2.4), 2)
        total_secs += est_sec

        motion = sc.camera_motion if sc.camera_motion in VALID_MOTIONS else VALID_MOTIONS[(idx - 1) % len(VALID_MOTIONS)]
        vis = re.sub(r"\s+", " ", (sc.visual_prompt_en or "").strip())
        if not vis:
            vis = f"Cinematic 9:16 shot illustrating: {clean_narr}"

        cleaned_scenes.append(
            ScriptSceneSpec(
                scene_number=idx,
                act=sc.act or ("hook" if idx <= 2 else "climax" if idx >= len(artifact.scenes) - 2 else "development"),
                narration=clean_narr,
                speech_text_tts=clean_narr,
                estimated_seconds=est_sec,
                visual_prompt_en=vis,
                include_character=bool(sc.include_character),
                camera_angle=sc.camera_angle or "cinematic medium shot",
                camera_motion=motion,
                on_screen_text=sc.on_screen_text or f"CENA {idx:02d}",
            )
        )

    if artifact.format_type == "short" and total_words > 165:
        notes.append(
            f"Roteiro com {total_words} palavras (~{total_secs:.1f}s em fala natural); considere enxugar caso deseje abaixo de 60s."
        )

    artifact.scenes = cleaned_scenes
    artifact.full_narration = " ".join(sc.narration for sc in cleaned_scenes if sc.narration).strip()
    artifact.word_count = total_words
    artifact.estimated_total_seconds = round(total_secs, 2)
    artifact.quality_notes = notes
    if cleaned_scenes and not artifact.hook:
        artifact.hook = cleaned_scenes[0].narration
    return artifact


class ScriptAgent(BaseMediaAgent):
    """
    Agente 1 — Roteiros Completos:
    Cria o roteiro completo, bíblia visual adaptativa, falas limpas calibradas para
    locução natural (sem acelerar TTS) e direção de cena/câmera.
    """

    stage = AgentStage.SCRIPT

    async def _generate_via_gemini(
        self,
        ctx: AgentContext,
        feedback: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not ctx.gemini_key or os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") == "1":
            return None

        import asyncio
        from google import genai
        from google.genai import types

        is_short = ctx.format_type == "short"
        target_scenes_rule = (
            "EXATAMENTE 16 a 18 cenas sequenciais (para vídeo vertical de 50-58 segundos). "
            "Cada cena deve ter UMA frase falada natural em português com 6 a 9 palavras (total do roteiro entre 115 e 145 palavras)."
            if is_short
            else "12 a 16 blocos narrativos em 5 atos com alta retenção e mini-cliffhangers."
        )

        feedback_block = f"\nAJUSTES SOLICITADOS PELO REVISOR HUMANO:\n{feedback}\n" if feedback else ""
        biz_block = (
            f"Negócio: {ctx.business_name} | Nicho: {ctx.business_niche or 'Geral'} | "
            f"Arquétipo: {ctx.business_archetype or 'dark_channel'}"
        )

        sys_prompt = f"""Você é o Agente Especialista em Roteiros Completos e Direção Cinematográfica.
Sua única missão é escrever um roteiro impecável para locução humana em Português do Brasil e dirigir cada tomada visual.

REGRAS CRÍTICAS DE ESCRITA ORAL (FALA NATURAL):
1. Escreva para o OUVIDO, não para leitura acadêmica: frases curtas, diretas, rítmicas e conectadas entre si.
2. {target_scenes_rule}
3. PROIBIDO usar colchetes `[pausa]`, parênteses `(fase 2)`, prefixos `Cena 1:`, emojis ou markdown dentro de `narration`.
4. Evite palavras estrangeiras difíceis ou siglas sem explicação; se usar números, escreva de forma natural.
5. A última cena deve concluir ou fazer looping natural com o gancho inicial.

REGRAS CRÍTICAS DE DIREÇÃO VISUAL (`visual_bible` + `scenes`):
1. `visual_bible.art_style` DEVE respeitar o estilo pedido ({ctx.visual_style or 'adequado ao tema, sem forçar anime se o tema for realista/documental/tech'}).
2. Alterne os enquadramentos (`camera_angle`): plano aberto monumental, plano médio com regra dos terços, over-the-shoulder, plano detalhe de objeto/cenário.
3. Defina `include_character` como `false` quando a cena for um plano detalhe de objeto, paisagem ampla ou arquitetura sem personagem, e `true` quando o personagem estiver em cena.
4. Escolha `camera_motion` dentre: `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `tilt_up`.

Retorne APENAS JSON válido no formato:
{{
  "title": "Título do vídeo",
  "hook": "Frase de gancho dos primeiros 3 segundos",
  "cta": "Fecho ou frase de looping",
  "suggested_music_mood": "Clima sugerido (metadado)",
  "seo_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "visual_bible": {{
    "protagonist_description": "Descrição física e vestuário consistentes em inglês",
    "world_setting": "Ambiente, arquitetura, clima e atmosfera específicos em inglês",
    "color_palette": "Paleta de cores dominante em inglês",
    "art_style": "Estilo visual exato em inglês",
    "lighting_mood": "Direção de luz em inglês",
    "negative_constraints": "no text, no watermark, no split screen, no distorted anatomy"
  }},
  "scenes": [
    {{
      "scene_number": 1,
      "act": "hook",
      "narration": "Frase natural em português com seis a nove palavras.",
      "visual_prompt_en": "Detailed English visual prompt with camera angle, environment and lighting, vertical 9:16",
      "include_character": true,
      "camera_angle": "Wide establishing shot",
      "camera_motion": "zoom_in",
      "on_screen_text": "GANCHO"
    }}
  ]
}}"""

        user_msg = (
            f"{biz_block}\n"
            f"Título: {ctx.title}\n"
            f"Tema / Pauta: {ctx.topic or ctx.context_text or ctx.title}\n"
            f"Tom: {ctx.tone}\n"
            f"Estilo Visual Solicitado: {ctx.visual_style or 'Definir o mais aderente ao tema'}\n"
            f"Plataforma: {ctx.target_platform} ({ctx.format_type})\n"
            f"{feedback_block}"
            "Gere agora o roteiro completo e cinematográfico em JSON."
        )

        def _sync_generate() -> Optional[Dict[str, Any]]:
            client = genai.Client(
                api_key=ctx.gemini_key,
                http_options=types.HttpOptions(timeout=15000),
            )
            for model_cand in ("gemini-2.5-flash", "gemini-3.8-flash", "gemini-2.0-flash"):
                try:
                    response = client.models.generate_content(
                        model=model_cand,
                        contents=[f"{sys_prompt}\n\n{user_msg}"],
                        config=types.GenerateContentConfig(
                            temperature=0.7,
                            response_mime_type="application/json",
                        ),
                    )
                    raw_txt = (getattr(response, "text", None) or "").strip()
                    if "```json" in raw_txt:
                        raw_txt = raw_txt.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw_txt:
                        raw_txt = raw_txt.split("```")[1].split("```")[0].strip()
                    if raw_txt:
                        parsed_obj = json.loads(raw_txt)
                        if isinstance(parsed_obj, dict) and isinstance(parsed_obj.get("scenes"), list) and len(parsed_obj["scenes"]) >= 4:
                            return parsed_obj
                except Exception as inner_exc:
                    logger.debug(f"[ScriptAgent] Modelo {model_cand} falhou: {inner_exc}")
                    continue
            return None

        try:
            loop = asyncio.get_running_loop()
            return await asyncio.wait_for(loop.run_in_executor(None, _sync_generate), timeout=35.0)
        except Exception as exc:
            logger.warning(f"[ScriptAgent] Falha ao gerar roteiro via Gemini: {exc}")
        return None

    async def run(
        self,
        ctx: AgentContext,
        manifest: PipelineManifest,
        preexisting_scenes: Optional[List[Dict[str, Any]]] = None,
        preexisting_bible: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None,
        force_regenerate: bool = False,
    ) -> PipelineManifest:
        await self.notify(ctx, 10.0, "Agente 1 (Roteiro): Estruturando narrativa, falas e bíblia visual...")

        if manifest.script and not force_regenerate and not feedback:
            manifest.script = validate_and_polish_script(manifest.script)
            manifest.stage_statuses[self.stage.value] = "completed"
            await self.notify(ctx, 100.0, "Agente 1 (Roteiro): Roteiro validado e pronto.")
            return manifest

        raw_data: Optional[Dict[str, Any]] = None
        if preexisting_scenes and not force_regenerate and not feedback:
            raw_data = {
                "title": ctx.title,
                "visual_bible": preexisting_bible or {},
                "scenes": preexisting_scenes,
            }
        else:
            raw_data = await self._generate_via_gemini(ctx, feedback=feedback)

        if not raw_data:
            fallback_scenes = _build_structured_fallback_scenes(ctx.title, ctx.topic or ctx.context_text, ctx.format_type)
            raw_data = {
                "title": ctx.title,
                "hook": fallback_scenes[0]["narration"],
                "cta": fallback_scenes[-1]["narration"],
                "seo_tags": ["historia", "curiosidades", "shorts"],
                "visual_bible": preexisting_bible or {},
                "scenes": fallback_scenes,
            }

        visual_bible = _build_adaptive_visual_bible(
            title=raw_data.get("title") or ctx.title,
            topic=ctx.topic or ctx.context_text or ctx.title,
            niche=ctx.business_niche,
            requested_style=ctx.visual_style,
            raw_bible=raw_data.get("visual_bible") if isinstance(raw_data.get("visual_bible"), dict) else preexisting_bible,
        )

        scene_specs: List[ScriptSceneSpec] = []
        for idx, raw_sc in enumerate(raw_data.get("scenes") or [], start=1):
            narr = clean_narration_for_tts(
                raw_sc.get("narration") or raw_sc.get("script") or raw_sc.get("description") or f"Cena {idx}."
            )
            vis = (
                raw_sc.get("visual_prompt_en")
                or raw_sc.get("visual_prompt")
                or raw_sc.get("b_roll_description")
                or f"Cinematic 9:16 shot depicting: {narr}"
            )
            motion = raw_sc.get("camera_motion") or VALID_MOTIONS[(idx - 1) % len(VALID_MOTIONS)]
            if motion not in VALID_MOTIONS:
                motion = VALID_MOTIONS[(idx - 1) % len(VALID_MOTIONS)]
            scene_specs.append(
                ScriptSceneSpec(
                    scene_number=idx,
                    act=str(raw_sc.get("act") or "development"),
                    narration=narr,
                    speech_text_tts=narr,
                    visual_prompt_en=str(vis),
                    include_character=bool(raw_sc.get("include_character", True)),
                    camera_angle=str(raw_sc.get("camera_angle") or "cinematic shot"),
                    camera_motion=motion,  # type: ignore[arg-type]
                    on_screen_text=str(raw_sc.get("on_screen_text") or raw_sc.get("title") or f"CENA {idx:02d}"),
                )
            )

        artifact = ScriptArtifact(
            title=str(raw_data.get("title") or ctx.title),
            topic=ctx.topic or ctx.context_text or ctx.title,
            format_type="long" if ctx.format_type == "long" else "short",
            target_platform=ctx.target_platform,
            hook=str(raw_data.get("hook") or (scene_specs[0].narration if scene_specs else "")),
            cta=str(raw_data.get("cta") or (scene_specs[-1].narration if scene_specs else "")),
            voice_persona=ctx.voice_persona or "pt-BR-AntonioNeural",
            seo_tags=[str(t) for t in (raw_data.get("seo_tags") or [])][:10],
            visual_bible=visual_bible,
            scenes=scene_specs,
        )
        manifest.script = validate_and_polish_script(artifact)
        manifest.stage_statuses[self.stage.value] = "completed"
        await self.notify(
            ctx,
            100.0,
            f"Agente 1 (Roteiro): {len(manifest.script.scenes)} cenas e {manifest.script.word_count} palavras concluídas (~{manifest.script.estimated_total_seconds}s).",
        )
        return manifest

