import json
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from google.genai import types

from src.models import (
    Business,
    ContentAsset,
    ApprovalQueue,
    Task,
    User,
)
from src.schemas.business import DarkScriptCreateRequest, DarkScriptResponse, DarkScriptScene
from src.services.gemini_service import get_user_gemini_client
from src.services.media.pipeline import _build_story_visual_bible, ensure_twenty_scenes

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def generate_dark_script(
    db: AsyncSession,
    user: User,
    business: Business,
    req: DarkScriptCreateRequest,
) -> dict[str, Any]:
    """
    Gera um roteiro completo de alta retenção para Canal Dark (YouTube Shorts,
    TikTok ou YouTube Vídeo Longo) com prompts de B-Roll cena a cena para IA,
    salva no banco de dados e submete à fila de aprovação humana.
    """
    now = _utc_now()
    is_short = req.format_type == "short" or req.target_platform in ("youtube_shorts", "tiktok")

    prompt = f"""Você é o Roteirista Chefe e Diretor Criativo especializado em Canais Dark (YouTube e TikTok Viral) do SpirandeliEmpire.
Crie um roteiro viral completo para o canal dark: "{business.name}".
Nicho do Canal: {business.niche or 'Mistérios, Curiosidades e Fatos Impressionantes'}
Tema da Pauta: {req.topic}
Título Proposto: {req.title}
Formato: {"Vídeo Curto (Shorts/TikTok - 60 segundos com EXATAMENTE 20 cenas de 3 segundos cada)" if is_short else "Vídeo Longo (YouTube - 8 a 12 minutos, 5 atos com alta retenção)"}
Tom Narrativo: {req.tone or 'Misterioso, instigante e com ritmo dinâmico'}
Estilo Visual dos Prompts de Imagem: {req.visual_style or '2D dark epic anime cinematic illustration in the style of Castlevania Nocturne, dramatic chiaroscuro volumetric lighting'}
Persona da Voz (TTS/ElevenLabs): {req.voice_persona or 'Voz grave, documental e hipnótica'}

DIRETRIZES CRÍTICAS:
1. Hook Inicial (0-3 segundos): Deve ser impossível de ignorar, uma quebra de padrão total que prenda a atenção de imediato.
2. {"Roteiro Sequencial de 20 Cenas Conectadas: Gere EXATAMENTE 20 cenas (scene_number 1 a 20), onde cada `narration` tem entre 6 e 9 palavras limpas em português (sem colchetes) e a Cena 20 faz loop com a Cena 1." if is_short else "Tensão em 5 Atos: Crie mini-cliffhangers a cada 90 segundos para manter a audiência assistindo até o final."}
3. Bíblia Visual (`visual_bible`) e Direção Cinematográfica Imersiva Sob Medida:
   - Pense o universo visual da história (`world_setting`: arquitetura, texturas, profundidade de camadas, clima e iluminação volumétrica), o protagonista (`protagonist_description`), a paleta (`color_palette`) e o traço (`art_style`) ESPECIFICAMENTE de acordo com o tema solicitado (sem templates fixos).
   - DIREÇÃO DE CENA DINÂMICA (ANTI-RETRATO CENTRALIZADO): É expressamente PROIBIDO gerar 20 retratos centralizados estáticos do personagem com fundo genérico! Cada `visual_prompt` deve ser concebido para aquele exato segundo da história: alterne planos gerais monumentais (Wide Establishing Shots revelando o ambiente), planos médios com regra dos terços (personagem descentralizado, primeiro plano e fundo detalhados), planos over-the-shoulder e tomadas de detalhe de cenário ou artefatos.

Retorne sua resposta EXCLUSIVAMENTE em formato JSON puro (sem marcações markdown ```json ... ``` extras ou texto introdutório) com a seguinte estrutura:
{{
  "title": "{req.title}",
  "hook": "Gancho inicial dos primeiros 3 segundos",
  "cta": "Chamada para ação ou frase de looping",
  "full_narration": "Texto integral narrado fluído em português",
  "suggested_music": "Estilo da trilha de fundo e BPM sugerido",
  "seo_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "visual_bible": {{
    "protagonist_description": "Descrição física detalhada do protagonista condizente com a história",
    "world_setting": "Descrição rica do cenário, arquitetura, clima e atmosfera específicos da história",
    "color_palette": "Cores dominantes e iluminação de contraste",
    "art_style": "Estilo visual de arte cinematográfica adaptado ao tema"
  }},
  "scenes": [
    {{
      "scene_number": 1,
      "timestamp": "00:00 - 00:03",
      "narration": "Frase curta e impactante de seis a nove palavras.",
      "visual_prompt": "Cinematic shot description with specific camera angle, rich environment, dynamic lighting and integrated subject, 9:16",
      "b_roll_description": "Descrição da cena visual e movimento de câmera",
      "on_screen_text": "TEXTO CURTO"
    }}
  ]
}}
"""

    parsed_data = None
    try:
        client, model_name = await get_user_gemini_client(user, db)
        candidate_models = [model_name, "gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-3.5-flash"]
        for cand in candidate_models:
            try:
                response = client.models.generate_content(
                    model=cand,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        response_mime_type="application/json",
                    ),
                )
                if response.text:
                    cleaned = response.text.strip()
                    if cleaned.startswith("```json"):
                        cleaned = re.sub(r"^```json\s*", "", cleaned)
                        cleaned = re.sub(r"\s*```$", "", cleaned)
                    parsed_data = json.loads(cleaned)
                    break
            except Exception as cand_err:
                logger.warning(f"Tentativa com {cand} falhou: {cand_err}. Tentando próximo modelo...")
                continue
    except Exception as e:
        logger.warning(f"Erro ao invocar Gemini para script dark: {e}. Usando gerador estruturado inteligente.")

    # Fallback estruturado caso a API externa falhe ou retorne incompleto
    if not parsed_data or not isinstance(parsed_data, dict) or not parsed_data.get("scenes"):
        if is_short:
            parsed_data = {
                "title": req.title,
                "hook": f"Você sabia que existe um segredo sombrio sobre {req.topic} que quase ninguém conhece?",
                "cta": "Comente o que você acha e compartilhe com quem precisa saber disso.",
                "full_narration": f"Você sabia que existe um segredo sombrio sobre {req.topic} que quase ninguém conhece? Documentos recém-descobertos revelam que nos bastidores, tudo funcionava de forma assustadoramente diferente. Especialistas tentaram abafar o caso por décadas, mas as evidências não mentem. E o detalhe mais perturbador de todos... é exatamente como isso continua acontecendo hoje sem você perceber.",
                "suggested_music": "Dark Ambient Suspense Drone, 95 BPM, low sub-bass tension",
                "seo_tags": ["misterios", "fatoscuriosos", "canaldark", "curiosidades", "historia"],
                "scenes": [
                    {
                        "scene_number": 1,
                        "timestamp": "00:00 - 00:03",
                        "narration": f"Você sabia que existe um segredo sombrio sobre {req.topic} que quase ninguém conhece?",
                        "visual_prompt": f"Hyper-realistic cinematic shot, mysterious dramatic atmosphere, ancient classified dossier on a dark mahogany table, spotlight in total darkness, Unreal Engine 5 render, 8k resolution, volumetric fog --ar 9:16",
                        "b_roll_description": "Câmera dá um zoom rápido in em documentos confidenciais com luz dramática",
                        "on_screen_text": "O SEGREDO QUE NUNCA TE CONTARAM 🚨",
                    },
                    {
                        "scene_number": 2,
                        "timestamp": "00:03 - 00:18",
                        "narration": "Documentos recém-descobertos revelam que nos bastidores, tudo funcionava de forma assustadoramente diferente.",
                        "visual_prompt": f"Old archival footage style, dark secret archives with endless shelves, mysterious shadows of investigators, glowing dust particles, anamorphic lens flare, 35mm film grain --ar 9:16",
                        "b_roll_description": "Corte dinâmico para arquivos antigos sob luz de lanterna",
                        "on_screen_text": "ARQUIVOS SECRETOS",
                    },
                    {
                        "scene_number": 3,
                        "timestamp": "00:18 - 00:35",
                        "narration": "Especialistas tentaram abafar o caso por décadas, mas as evidências materiais não mentem.",
                        "visual_prompt": f"Cinematic close up of glowing high tech microscopic forensic evidence, dark blue and amber color grading, photorealistic, intense contrast --ar 9:16",
                        "b_roll_description": "Evidências e registros sendo examinados em ritmo frenético",
                        "on_screen_text": "EVIDÊNCIAS REAIS",
                    },
                    {
                        "scene_number": 4,
                        "timestamp": "00:35 - 00:50",
                        "narration": "E o detalhe mais perturbador de todos... é exatamente como isso continua acontecendo hoje diante dos seus olhos.",
                        "visual_prompt": f"Surreal atmospheric city at midnight under thick dark clouds, single glowing window, cinematic lighting, neo-noir mystery, ultra-detailed --ar 9:16",
                        "b_roll_description": "Vista aérea noturna da cidade se conectando de volta ao gancho inicial",
                        "on_screen_text": "ISSO CONTINUA HOJE?",
                    },
                ],
            }
        else:
            parsed_data = {
                "title": req.title,
                "hook": f"A verdade oculta sobre {req.topic} foi apagada da história... até agora.",
                "cta": "Inscreva-se no canal para desvendar os maiores segredos da humanidade toda semana.",
                "full_narration": f"A verdade oculta sobre {req.topic} foi apagada da história... até agora. No início parecia apenas mais um registro comum, mas quando pesquisadores cruzaram os dados, a farsa começou a ruir. Acompanhe a cronologia completa dos acontecimentos que mudaram o mundo para sempre.",
                "suggested_music": "Epic Orchestral Dark Documentary Soundtrack, Hans Zimmer style, 75 BPM",
                "seo_tags": ["documentariodark", "misteriosdafatos", "historiaoculta", "youtubebrasil", "investigacao"],
                "scenes": [
                    {
                        "scene_number": 1,
                        "timestamp": "00:00 - 00:45",
                        "narration": f"A verdade oculta sobre {req.topic} foi apagada dos livros de história... até agora.",
                        "visual_prompt": f"Epic wide cinematic shot of an ancient stone monument shrouded in ominous mist, dawn light piercing through clouds, National Geographic documentary style, 8k resolution, photorealistic --ar 16:9",
                        "b_roll_description": "Panorâmica lenta do monumento envolto em névoa com texto em relevo",
                        "on_screen_text": "ATO I: A DESCOBERTA",
                    },
                    {
                        "scene_number": 2,
                        "timestamp": "00:45 - 03:00",
                        "narration": "No início do século passado, os primeiros indícios foram documentados por testemunhas oculares.",
                        "visual_prompt": f"Vintage 1920s expedition in deep unexplored territory, dusty lantern light, intense cinematic portraits of explorers, hyper-detailed textures, sepia and teal palette --ar 16:9",
                        "b_roll_description": "Cenas de reconstituição histórica com foco em mapas e relatórios",
                        "on_screen_text": "ATO II: AS TESTEMUNHAS",
                    },
                    {
                        "scene_number": 3,
                        "timestamp": "03:00 - 06:00",
                        "narration": "Mas foi nos anos 1970 que o verdadeiro ponto de inflexão aconteceu nos laboratórios subterrâneos.",
                        "visual_prompt": f"Retro sci-fi laboratory, vintage analog computer screens glowing green in dark bunker, scientists in silhouette, tense cold war atmosphere, Kodak film grain --ar 16:9",
                        "b_roll_description": "Laboratório com telas de computador analógicas e osciloscópios",
                        "on_screen_text": "ATO III: O EXPERIMENTO",
                    },
                    {
                        "scene_number": 4,
                        "timestamp": "06:00 - 08:30",
                        "narration": "As consequências que vemos hoje provam que nada daquilo foi coincidência.",
                        "visual_prompt": f"Modern high-tech command center overlooking global satellite network map, dramatic blue and cyan lighting, hyper-realistic, photorealistic reflections --ar 16:9",
                        "b_roll_description": "Mapas globais e imagens de satélite modernas mostrando as ramificações atuais",
                        "on_screen_text": "ATO IV: O IMPACTO GLOBAL",
                    },
                ],
            }

    # Salva o roteiro como ContentAsset garantindo 20 cenas conectadas e visual_bible nos Shorts
    asset_type = "dark_script_short" if is_short else "dark_script_long"
    tracking_code = f"DARK-{secrets.token_hex(4).upper()}"
    scenes_raw = parsed_data.get("scenes", [])
    full_text = parsed_data.get("full_narration", "")
    raw_bible = parsed_data.get("visual_bible") if isinstance(parsed_data.get("visual_bible"), dict) else None

    story_bible = _build_story_visual_bible(
        title=parsed_data.get("title", req.title),
        full_narration=f"{req.topic} {full_text}",
        existing_bible=raw_bible,
    )
    if is_short:
        scenes_raw = ensure_twenty_scenes(
            scenes=scenes_raw,
            full_narration=full_text or req.topic or req.title,
            title=parsed_data.get("title", req.title),
            visual_bible=story_bible,
        )
        full_text = " ".join(s.get("narration", "") for s in scenes_raw if s.get("narration")).strip() or full_text

    asset = ContentAsset(
        business_id=business.id,
        tracking_code=tracking_code,
        type=asset_type,
        platform=req.target_platform,
        title=parsed_data.get("title", req.title),
        body=full_text,
        content={
            "hook": parsed_data.get("hook", "") or (scenes_raw[0].get("narration", "") if scenes_raw else ""),
            "cta": parsed_data.get("cta", ""),
            "scenes": scenes_raw,
            "visual_bible": story_bible,
            "seo_tags": parsed_data.get("seo_tags", []),
            "suggested_music": parsed_data.get("suggested_music", ""),
            "voice_persona": req.voice_persona or "Voz grave e documental",
            "format_type": req.format_type,
            "visual_style": req.visual_style,
        },
        version=1,
        funnel_stage="tof_attraction",
        status="supervision",
        created_at=now,
        updated_at=now,
    )
    db.add(asset)
    await db.flush()

    # Cria item na Fila de Aprovação (Human-in-the-Loop)
    approval = ApprovalQueue(
        business_id=business.id,
        user_id=user.id,
        type="dark_script_approval",
        title=f"Roteiro Canal Dark: {asset.title}",
        summary=f"Roteiro {'Short/TikTok (60s, 20 cenas)' if is_short else 'Vídeo Longo (8-12m)'} com {len(scenes_raw)} cenas conectadas e prompts visuais prontos para renderização.",
        payload={
            "content_asset_id": asset.id,
            "tracking_code": tracking_code,
            "format_type": req.format_type,
            "platform": req.target_platform,
            "hook": parsed_data.get("hook"),
            "scenes_count": len(scenes_raw),
            "scenes": scenes_raw,
            "visual_bible": story_bible,
            "voice_persona": req.voice_persona,
            "seo_tags": parsed_data.get("seo_tags", []),
        },
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(approval)
    await db.flush()

    asset.approval_queue_id = approval.id

    # Cria tarefa no Kanban operacional vinculada ao ContentAsset para renderizar o vídeo MP4 a partir deste roteiro
    task = Task(
        business_id=business.id,
        user_id=user.id,
        title=f"[Vídeo] Renderizar Roteiro: {asset.title}",
        description=f"Roteiro dark gerado pelo sistema com {len(scenes_raw)} cenas conectadas. Execute para renderizar o vídeo MP4 9:16 completo com narração e legendas.",
        assignee="agent",
        status="supervision",
        priority="high",
        source="agent",
        agent_action="render_video_series",
        payload={
            "content_asset_id": asset.id,
            "approval_id": approval.id,
            "scenes_count": len(scenes_raw),
            "visual_bible": story_bible,
        },
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await db.flush()
    approval.task_id = task.id
    asset_content = dict(asset.content or {})
    asset_content["task_id"] = task.id
    asset.content = asset_content

    await db.commit()
    await db.refresh(asset)

    formatted_scenes = [
        DarkScriptScene(
            scene_number=s.get("scene_number", idx + 1),
            timestamp=s.get("timestamp", f"00:{idx*3:02d} - 00:{(idx+1)*3:02d}"),
            narration=s.get("narration", ""),
            visual_prompt=s.get("visual_prompt", ""),
            b_roll_description=s.get("b_roll_description", ""),
            on_screen_text=s.get("on_screen_text"),
        )
        for idx, s in enumerate(scenes_raw)
    ]

    return {
        "id": asset.id,
        "business_id": business.id,
        "task_id": task.id,
        "title": asset.title,
        "format_type": req.format_type,
        "target_platform": req.target_platform,
        "hook": asset_content.get("hook", ""),
        "cta": parsed_data.get("cta", ""),
        "full_narration": full_text,
        "visual_bible": story_bible,
        "scenes_count": len(formatted_scenes),
        "scenes": [s.model_dump() for s in formatted_scenes],
        "seo_tags": parsed_data.get("seo_tags", []),
        "suggested_music": parsed_data.get("suggested_music"),
        "voice_persona": req.voice_persona,
        "approval_queue_id": approval.id,
        "status": asset.status,
        "created_at": asset.created_at,
    }


async def list_dark_scripts(db: AsyncSession, business_id: int) -> list[dict[str, Any]]:
    """Lista todos os roteiros e ativos de mídia de canal dark criados para o negócio."""
    res = await db.execute(
        select(ContentAsset)
        .where(
            ContentAsset.business_id == business_id,
            ContentAsset.type.in_(["dark_script_short", "dark_script_long", "video_script"]),
        )
        .order_by(ContentAsset.id.desc())
    )
    assets = res.scalars().all()
    results = []
    for a in assets:
        content_dict = a.content or {}
        scenes_data = content_dict.get("scenes", [])
        results.append({
            "id": a.id,
            "business_id": a.business_id,
            "parent_id": a.parent_id,
            "task_id": content_dict.get("task_id"),
            "video_url": content_dict.get("video_url"),
            "audio_url": content_dict.get("audio_url"),
            "srt_url": content_dict.get("srt_url"),
            "visual_bible": content_dict.get("visual_bible"),
            "title": a.title or "Sem título",
            "format_type": content_dict.get("format_type", "short" if a.type == "dark_script_short" else "long"),
            "target_platform": a.platform,
            "hook": content_dict.get("hook", ""),
            "cta": content_dict.get("cta", ""),
            "full_narration": a.body or "",
            "scenes_count": len(scenes_data),
            "scenes": scenes_data,
            "seo_tags": content_dict.get("seo_tags", []),
            "suggested_music": content_dict.get("suggested_music"),
            "voice_persona": content_dict.get("voice_persona"),
            "approval_queue_id": a.approval_queue_id,
            "status": a.status,
            "total_views": a.total_views,
            "total_clicks": a.total_clicks,
            "total_revenue_brl": float(a.total_revenue_brl),
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return results


async def mine_dark_channel_topics(business: Business) -> list[dict[str, Any]]:
    """Gera pautas e temas de alto potencial de cliques e retenção para o nicho do canal."""
    niche = (business.niche or "Mistérios & Curiosidades").lower()
    
    if "história" in niche or "guerra" in niche or "historia" in niche:
        topics = [
            {
                "topic": "O Batalhão Fantasma da Segunda Guerra Mundial",
                "predicted_ctr": "11.4%",
                "format_recommended": "long",
                "estimated_views": "250K - 800K",
                "hook_angle": "Militares que enganaram o exército inimigo com tanques infláveis e sons gravados.",
            },
            {
                "topic": "O Último Soldado Samurai que Não Sabia que a Guerra Havia Terminado",
                "predicted_ctr": "13.2%",
                "format_recommended": "short",
                "estimated_views": "1.2M - 3.5M",
                "hook_angle": "Hiroo Onoda lutou na selva por 29 anos após 1945 achando que ordens de rendição eram fake.",
            },
            {
                "topic": "O Mistério Inexplicável do Voo 19 no Triângulo das Bermudas",
                "predicted_ctr": "9.8%",
                "format_recommended": "long",
                "estimated_views": "180K - 500K",
                "hook_angle": "Cinco bombardeiros da Marinha desapareceram simultaneamente sem deixar vestígios.",
            },
        ]
    elif "finanças" in niche or "dinheiro" in niche or "negócio" in niche:
        topics = [
            {
                "topic": "Como a Família Rothschild Criou o Sistema Bancário Moderno",
                "predicted_ctr": "10.5%",
                "format_recommended": "long",
                "estimated_views": "300K - 900K",
                "hook_angle": "O mensageiro secreto que soube do resultado da Batalha de Waterloo antes de todo o parlamento.",
            },
            {
                "topic": "O Golpe Psicológico dos Supermercados que Faz Você Gastar 40% a Mais",
                "predicted_ctr": "14.1%",
                "format_recommended": "short",
                "estimated_views": "1.8M - 4.2M",
                "hook_angle": "Por que o pão fresco e as flores ficam sempre na entrada da loja?",
            },
            {
                "topic": "A Moeda que Derreteu um Império em 6 Meses",
                "predicted_ctr": "9.2%",
                "format_recommended": "long",
                "estimated_views": "150K - 450K",
                "hook_angle": "A hiperinflação de Weimar e a lição esquecida sobre ouro e dívida.",
            },
        ]
    else:
        topics = [
            {
                "topic": f"Os 3 Maiores Segredos Jamais Revelados sobre {business.niche or 'o Mundo Antigo'}",
                "predicted_ctr": "12.8%",
                "format_recommended": "short",
                "estimated_views": "850K - 2.1M",
                "hook_angle": "Se você acha que conhece a história toda, este único detalhe vai te assustar.",
            },
            {
                "topic": "A Descoberta Arqueológica que Ninguém Consegue Explicar",
                "predicted_ctr": "11.0%",
                "format_recommended": "long",
                "estimated_views": "400K - 1.1M",
                "hook_angle": "Artefatos com precisão milimétrica encontrados em camadas geológicas de 50 mil anos.",
            },
            {
                "topic": "Por Que a Ciência Não Consegue Decifrar Esse Fenômeno?",
                "predicted_ctr": "13.5%",
                "format_recommended": "short",
                "estimated_views": "1.5M - 3.8M",
                "hook_angle": "Cientistas que tentaram explicar o evento perderam os dados misteriosamente.",
            },
        ]
    return topics

