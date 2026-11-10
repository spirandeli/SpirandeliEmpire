import asyncio
import base64
import io
import json
import logging
import math
import os
import random
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageStat
import httpx
from google import genai
from google.genai import types

logger = logging.getLogger("abvos.media.images")

# Cache com cooldown por (chave, modelo) para não bloquear permanentemente a chave Gemini em erros transitórios
_UNAVAILABLE_IMAGEN_KEYS: set[str] = set()
_GEMINI_IMAGE_MODEL_COOLDOWN: Dict[tuple[str, str], float] = {}

# Controle de janela de rate-limit por provedor (evita chamadas desnecessárias em cooldown)
_POLLINATIONS_NEXT_AVAILABLE_AT: float = 0.0
_HF_SPACE_COOLDOWN_UNTIL: Dict[str, float] = {}


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def create_cinematic_dark_backdrop(
    width: int = 1080,
    height: int = 1920,
    scene_number: int = 1,
    title: str = "",
    prompt: str = "",
    theme_color: str = "#0f172a",
) -> Image.Image:
    """
    Cria uma ilustração procedural 9:16 (1080x1920) com estética Dark Anime / Epic Cinema:
    - Iluminação volumétrica, halo celestial, silhueta de personagem místico/angelical,
      arquitetura gótica/montanhosa em camadas, feixes de luz e partículas em brasa.
    - NUNCA imprime caixas de texto ou prompts em inglês na tela (as legendas dinâmicas
      são renderizadas separadamente via FFmpeg/ASS).
    Usado apenas quando ABVOS_DISABLE_EXTERNAL_IMAGE_API=1 (testes) ou todas as APIs estiverem offline.
    """
    base = Image.new("RGB", (width, height), color="#020617")
    draw = ImageDraw.Draw(base)

    palettes = [
        ((8, 12, 28), (38, 18, 78), (135, 18, 38), (251, 191, 36)),    # Dark Indigo, Crimson & Gold
        ((4, 20, 38), (12, 52, 82), (8, 95, 142), (125, 211, 252)),     # Abyssal Cyan & Celestial Ice
        ((14, 12, 18), (58, 12, 12), (160, 62, 12), (252, 211, 77)),    # Obsidian, Hellfire & Amber
        ((8, 18, 30), (14, 65, 55), (16, 135, 105), (167, 243, 208)),   # Shadow Emerald & Mystic Mint
        ((12, 10, 26), (52, 22, 92), (98, 36, 150), (216, 180, 254)),   # Void Violet & Astral Lavender
    ]
    c1, c2, c3, accent = palettes[scene_number % len(palettes)]

    # 1. Gradiente atmosférico profundo
    for y in range(height):
        factor = y / height
        if factor < 0.55:
            t = factor / 0.55
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
        else:
            t = (factor - 0.55) / 0.45
            r = int(c2[0] * (1 - t) + c3[0] * t)
            g = int(c2[1] * (1 - t) + c3[1] * t)
            b = int(c2[2] * (1 - t) + c3[2] * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    cx = width // 2
    cy = int(height * 0.40)
    random.seed(scene_number * 1337)

    # 2. Feixes de luz volumétricos vindo do topo
    for i in range(9):
        spread = (i - 4) * 140 + random.randint(-25, 25)
        overlay_draw.polygon(
            [
                (cx - 40, 0),
                (cx + 40, 0),
                (cx + spread + 160, height),
                (cx + spread - 160, height),
            ],
            fill=(*accent, 16),
        )

    # Halo luminoso de contraluz (rim light)
    for radius in range(520, 90, -25):
        alpha = int(65 * (1 - radius / 520))
        overlay_draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*accent, alpha),
        )

    # 3. Silhueta de montanhas / catedrais góticas ao fundo
    for layer_idx, (base_y, amp, col_alpha) in enumerate([
        (int(height * 0.66), 110, (12, 16, 30, 195)),
        (int(height * 0.73), 85, (6, 9, 18, 235)),
        (int(height * 0.80), 55, (2, 4, 10, 255)),
    ]):
        pts = [(0, height), (0, base_y)]
        step = 45
        for x in range(0, width + step, step):
            wave = math.sin((x * 0.008) + scene_number + layer_idx * 1.7) * amp
            jag = random.randint(-28, 28)
            pts.append((min(width, x), int(base_y + wave + jag)))
        pts.append((width, height))
        overlay_draw.polygon(pts, fill=col_alpha)

    # 4. Silhueta dramática central (Arcanjo / Guardião / Entidade em contraluz)
    fig_dark = (5, 7, 15, 250)
    wing_span = 420 + (scene_number % 3) * 35
    # Asas estilizadas em camadas
    for w_idx in range(7):
        drop = w_idx * 48
        reach = wing_span - (w_idx * 38)
        # Asa esquerda
        overlay_draw.polygon(
            [
                (cx - 25, cy - 30 + drop // 3),
                (cx - reach, cy - 220 + drop),
                (cx - reach + 45, cy - 150 + drop),
                (cx - 35, cy + 40 + drop // 2),
            ],
            fill=fig_dark,
            outline=(*accent, 90),
        )
        # Asa direita
        overlay_draw.polygon(
            [
                (cx + 25, cy - 30 + drop // 3),
                (cx + reach, cy - 220 + drop),
                (cx + reach - 45, cy - 150 + drop),
                (cx + 35, cy + 40 + drop // 2),
            ],
            fill=fig_dark,
            outline=(*accent, 90),
        )

    # Corpo, manto e cabeça em silhueta
    overlay_draw.ellipse([cx - 42, cy - 135, cx + 42, cy - 50], fill=fig_dark, outline=(*accent, 150), width=2)
    overlay_draw.polygon(
        [
            (cx - 68, cy - 45),
            (cx + 68, cy - 45),
            (cx + 135, int(height * 0.82)),
            (cx - 135, int(height * 0.82)),
        ],
        fill=fig_dark,
    )
    # Olhos brilhantes sutis
    overlay_draw.ellipse([cx - 18, cy - 95, cx - 6, cy - 88], fill=(*accent, 240))
    overlay_draw.ellipse([cx + 6, cy - 95, cx + 18, cy - 88], fill=(*accent, 240))

    # 5. Partículas e brasas flutuantes
    for _ in range(110):
        px = random.randint(30, width - 30)
        py = random.randint(80, height - 120)
        p_rad = random.randint(2, 6)
        p_alpha = random.randint(70, 215)
        overlay_draw.ellipse(
            [px - p_rad, py - p_rad, px + p_rad, py + p_rad],
            fill=(*accent, p_alpha),
        )

    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    base = base.filter(ImageFilter.GaussianBlur(radius=0.8))

    # 6. Vinheta cinematográfica limpa (sem qualquer texto ou caixa HUD)
    hud = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    hud_draw = ImageDraw.Draw(hud)
    for r in range(0, 120):
        v_alpha = int(175 * (1 - r / 120))
        hud_draw.rectangle([r, r, width - r, height - r], outline=(0, 0, 0, v_alpha), width=2)

    base = Image.alpha_composite(base.convert("RGBA"), hud).convert("RGB")
    return base


def _is_visually_coherent_image(rgb: Image.Image) -> bool:
    """
    Rejeita imagens corrompidas, quase monocromáticas ou borrões abstratos sem nitidez/bordas
    (como os borrões sem forma que ocorriam em modelos SD 1.5 de baixa resolução).
    """
    try:
        stat = ImageStat.Stat(rgb)
        if max(stat.stddev) < 11.0:
            return False
        edges = rgb.convert("L").filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        if edge_stat.mean[0] < 2.8 and edge_stat.stddev[0] < 5.5:
            return False
        return True
    except Exception:
        return True


def _compose_square_to_9x16_seamless(
    sq_img: Image.Image,
    width: int = 1080,
    height: int = 1920,
) -> Image.Image:
    """
    Converte uma imagem quadrada (1:1, ex: 1024x1024) em vertical 9:16 (1080x1920)
    preservando 100% da proporção original (sem esticar rostos e sem amputar asas/braços nas laterais),
    fundindo o topo e a base com extensão atmosférica desfocada e vinheta cinematográfica para legendas.
    """
    bg = ImageOps.fit(sq_img, (width, height), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=28))
    bg = ImageEnhance.Brightness(bg).enhance(0.52)

    fg_h = 1480
    iw, ih = sq_img.size
    fg_w = int(iw * (fg_h / max(ih, 1)))
    if fg_w < width:
        fg_w = width
        fg_h = int(ih * (width / max(iw, 1)))
    fg = sq_img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
    left = max(0, (fg_w - width) // 2)
    fg = fg.crop((left, 0, left + width, min(fg_h, height)))

    mask = Image.new("L", fg.size, 255)
    fade_top = 110
    fade_bot = 165
    px = mask.load()
    for y in range(fg.size[1]):
        alpha = 255
        if y < fade_top:
            alpha = int(255 * (y / fade_top) ** 1.5)
        elif y > fg.size[1] - fade_bot:
            alpha = int(255 * ((fg.size[1] - y) / fade_bot) ** 1.5)
        if alpha < 255:
            for x in range(fg.size[0]):
                px[x, y] = alpha

    y_offset = max(0, (height - fg.size[1]) // 2 - 40)
    bg.paste(fg, (0, y_offset), mask)
    return bg


def _save_and_normalize_image_bytes(
    raw_bytes: bytes,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    trim_bottom_watermark: bool = False,
) -> bool:
    """
    Valida se os bytes recebidos são uma imagem real íntegra e com nitidez mínima,
    remove eventuais marcas d'água de rodapé e normaliza para 1080x1920 (9:16)
    SEM esticar ou deformar o rosto/corpo dos personagens:
    - Imagens nativas 9:16 (ex: 576x1024 do Flux.1-Schnell) usam resize LANCZOS direto.
    - Imagens 1:1 (ex: 1024x1024 do Pollinations) usam composição atmosférica sem perda lateral.
    """
    if not raw_bytes or len(raw_bytes) < 2048:
        return False
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            rgb = img.convert("RGB")
            if trim_bottom_watermark:
                iw, ih = rgb.size
                crop_x = int(iw * 0.02)
                crop_bottom = int(ih * 0.94)
                rgb = rgb.crop((crop_x, 0, iw - crop_x, crop_bottom))
            if not _is_visually_coherent_image(rgb):
                logger.warning("Imagem descartada por baixa nitidez ou borrão abstrato sem detalhes.")
                return False
            iw, ih = rgb.size
            if (iw, ih) != (width, height):
                aspect = iw / max(ih, 1)
                target_aspect = width / max(height, 1)
                if abs(aspect - target_aspect) <= 0.06:
                    rgb = rgb.resize((width, height), Image.Resampling.LANCZOS)
                elif aspect >= 0.82:
                    rgb = _compose_square_to_9x16_seamless(rgb, width=width, height=height)
                else:
                    rgb = ImageOps.fit(
                        rgb,
                        (width, height),
                        method=Image.Resampling.LANCZOS,
                        centering=(0.5, 0.35),
                    )
            rgb.save(output_path, "JPEG", quality=92)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 2048
    except Exception as e:
        logger.warning(f"Falha ao validar/normalizar imagem recebida: {e}")
        return False


def _build_styled_prompt(
    prompt: str,
    visual_bible: Optional[Dict[str, str]] = None,
    include_character: bool = True,
) -> str:
    """
    Constrói um prompt cinematográfico equilibrado, garantindo riqueza de cenário (Worldbuilding),
    enquadramentos cinematográficos em camadas (foreground/midground/background) e respeito ao
    `art_style` definido pela Bíblia Visual (sem impor estilo fixo quando outro estilo foi pedido).
    """
    clean_prompt = re.sub(r"\s+", " ", (prompt or "").split("--ar")[0]).strip()
    clean_prompt = re.sub(r"consistent character (?:design )?sheet,?\s*", "", clean_prompt, flags=re.IGNORECASE)

    parts: List[str] = [clean_prompt]
    art_style = "cinematic film still, high detail, dramatic volumetric lighting"
    negative_constraints = "no centered passport portrait, no plain background, no empty wall, no watermark, no text, no split screen"

    if visual_bible:
        protagonist = (visual_bible.get("protagonist_description") or "").strip()
        world_setting = (visual_bible.get("world_setting") or "").strip()
        color_palette = (visual_bible.get("color_palette") or "").strip()
        vb_style = (visual_bible.get("art_style") or "").strip()
        vb_negative = (visual_bible.get("negative_constraints") or "").strip()

        if include_character and protagonist and protagonist.lower()[:24] not in clean_prompt.lower():
            parts.append(f"Character (off-center, integrated): {protagonist}")
        if world_setting and world_setting.lower()[:20] not in clean_prompt.lower():
            parts.append(f"Environment: {world_setting}")
        if color_palette and color_palette.lower()[:18] not in clean_prompt.lower():
            parts.append(f"Palette: {color_palette}")
        if vb_style:
            art_style = vb_style
        if vb_negative:
            negative_constraints = f"{negative_constraints}, {vb_negative}"

    combined = ". ".join(p.rstrip(".") for p in parts if p)
    combined = combined[:950].strip()

    style_suffix = ""
    if art_style.lower()[:18] not in combined.lower():
        style_suffix = f", {art_style}"

    return (
        f"{combined}{style_suffix}, "
        "rule of thirds composition, deep environmental perspective, rich detailed background, "
        f"sharp focus, vertical 9:16 aspect ratio, {negative_constraints}"
    )


async def _try_google_genai_image(
    prompt: str,
    output_path: str,
    api_key: str,
    scene_number: int,
    timeout: float = 35.0,
    visual_bible: Optional[Dict[str, str]] = None,
    include_character: bool = True,
    max_attempts: int = 2,
) -> bool:
    """
    Provedor Principal (Gemini / Imagen): Gera imagem nativa 9:16 via Google GenAI
    (Gemini Flash Image com ImageConfig 9:16 e Imagen 3).
    Usa cooldown por (chave, modelo) em vez de bloquear permanentemente a chave inteira.
    """
    if os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") == "1":
        return False
    if not api_key or api_key in _UNAVAILABLE_IMAGEN_KEYS:
        return False

    enhanced_prompt = _build_styled_prompt(
        prompt,
        visual_bible=visual_bible,
        include_character=include_character,
    )

    def _is_model_cooled_down(model_name: str) -> bool:
        until = _GEMINI_IMAGE_MODEL_COOLDOWN.get((api_key, model_name), 0.0)
        return time.monotonic() < until

    def _set_model_cooldown(model_name: str, seconds: float) -> None:
        _GEMINI_IMAGE_MODEL_COOLDOWN[(api_key, model_name)] = time.monotonic() + seconds

    def _sync_call() -> Optional[bytes]:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=20000),
        )

        # 1. Tenta Gemini Flash Image Generation (com ImageConfig 9:16 nativo)
        gemini_image_models = (
            "gemini-2.5-flash-image",
            "gemini-2.0-flash-preview-image-generation",
        )
        for model_name in gemini_image_models:
            if _is_model_cooled_down(model_name):
                continue
            try:
                cfg = types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="9:16"),
                )
            except Exception:
                cfg = types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                )
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=enhanced_prompt,
                    config=cfg,
                )
                for cand in getattr(resp, "candidates", []) or []:
                    for part in getattr(cand.content, "parts", []) or []:
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            return inline.data
            except Exception as ex:
                err_str = str(ex).lower()
                if any(k in err_str for k in ("404", "not_found")):
                    _set_model_cooldown(model_name, 3600.0)
                    continue
                if any(k in err_str for k in ("429", "resource_exhausted", "quota")):
                    _set_model_cooldown(model_name, 30.0)
                    continue
                if any(k in err_str for k in ("403", "billing", "permission")):
                    _set_model_cooldown(model_name, 300.0)
                    continue
                logger.debug(f"[Cena #{scene_number}] Erro Gemini {model_name}: {ex}")
                continue

        # 2. Tenta Imagen 3 com aspect_ratio 9:16 nativo
        for imagen_model in ("imagen-3.0-generate-002", "imagen-3.0-fast-generate-001"):
            if _is_model_cooled_down(imagen_model):
                continue
            try:
                img_resp = client.models.generate_images(
                    model=imagen_model,
                    prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="9:16",
                        output_mime_type="image/jpeg",
                    ),
                )
                gen_imgs = getattr(img_resp, "generated_images", None) or []
                if gen_imgs:
                    image_obj = getattr(gen_imgs[0], "image", None)
                    img_bytes = getattr(image_obj, "image_bytes", None)
                    if img_bytes:
                        return img_bytes
            except Exception as ex:
                err_str = str(ex).lower()
                if any(k in err_str for k in ("404", "not_found")):
                    _set_model_cooldown(imagen_model, 3600.0)
                elif any(k in err_str for k in ("429", "resource_exhausted", "quota")):
                    _set_model_cooldown(imagen_model, 30.0)
                elif any(k in err_str for k in ("403", "billing", "permission")):
                    _set_model_cooldown(imagen_model, 300.0)
                continue
        return None

    loop = asyncio.get_running_loop()
    for attempt in range(max(1, max_attempts)):
        try:
            img_bytes = await asyncio.wait_for(loop.run_in_executor(None, _sync_call), timeout=timeout)
            if img_bytes and _save_and_normalize_image_bytes(img_bytes, output_path):
                logger.info(f"[Cena #{scene_number}] Imagem real gerada via Google GenAI (tentativa {attempt + 1}): {output_path}")
                return True
        except Exception as e:
            logger.warning(f"[Cena #{scene_number}] Google GenAI Image tentativa {attempt + 1} falhou ({e})")
        if attempt + 1 < max_attempts:
            await asyncio.sleep(1.5 * (attempt + 1))

    return False


async def _try_hf_gradio_flux_image(
    prompt: str,
    output_path: str,
    scene_number: int,
    timeout: float = 28.0,
    visual_bible: Optional[Dict[str, str]] = None,
    story_seed: int = 424242,
) -> bool:
    """
    Provedor 2: Gera imagem 9:16 real usando Spaces oficiais Flux.1 / SD3.5 no HuggingFace Gradio API.
    Mantém SEMPRE a mesma prioridade de modelo (sem rotacionar por cena) e usa story_seed fixa
    para preservar o mesmo traço artístico e personagem em todo o vídeo.
    """
    if os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") == "1":
        return False

    styled_prompt = _build_styled_prompt(prompt, visual_bible=visual_bible)
    seed = int(story_seed) + scene_number

    spaces = [
        {
            "name": "flux-1-schnell",
            "base": "https://black-forest-labs-flux-1-schnell.hf.space",
            "endpoint": "/gradio_api/call/infer",
            "data": [styled_prompt, seed, False, 768, 1344, 4],
        },
        {
            "name": "flux-1-merged",
            "base": "https://multimodalart-flux-1-merged.hf.space",
            "endpoint": "/gradio_api/call/infer",
            "data": [styled_prompt, seed, False, 768, 1344, 3.5, 8],
        },
        {
            "name": "sd-3.5-large-turbo",
            "base": "https://stabilityai-stable-diffusion-3-5-large-turbo.hf.space",
            "endpoint": "/gradio_api/call/infer",
            "data": [
                styled_prompt,
                "text, watermark, letters, signature, blurry, low quality, deformed, inconsistent character, different person, b&w manga sketch, photorealistic photo",
                seed,
                False,
                576,
                1024,
                1.5,
                4,
            ],
        },
    ]

    hf_token = (os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY") or "").strip()
    headers = {"Content-Type": "application/json"}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    now = time.monotonic()
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for sp in spaces:
            cooldown_until = _HF_SPACE_COOLDOWN_UNTIL.get(sp["name"], 0.0)
            if now < cooldown_until:
                continue

            call_url = f"{sp['base']}{sp['endpoint']}"
            try:
                r = await client.post(call_url, json={"data": sp["data"]}, headers=headers)
                if r.status_code != 200:
                    _HF_SPACE_COOLDOWN_UNTIL[sp["name"]] = time.monotonic() + 45.0
                    continue
                event_id = r.json().get("event_id")
                if not event_id:
                    continue

                stream_url = f"{call_url}/{event_id}"
                r2 = await client.get(stream_url, headers=headers)
                text_body = r2.text
                if "event: error" in text_body or "ZeroGPU quota" in text_body:
                    _HF_SPACE_COOLDOWN_UNTIL[sp["name"]] = time.monotonic() + 65.0
                    continue

                img_url = None
                for line in text_body.splitlines():
                    if line.startswith("data: "):
                        raw_json = line[6:].strip()
                        try:
                            parsed = json.loads(raw_json)
                            if isinstance(parsed, list) and parsed:
                                first = parsed[0]
                                if isinstance(first, dict):
                                    img_url = first.get("url") or (
                                        f"{sp['base']}/gradio_api/file={first['path']}" if first.get("path") else None
                                    )
                                    break
                        except Exception:
                            pass

                if img_url:
                    img_resp = await client.get(img_url)
                    if img_resp.status_code == 200 and _save_and_normalize_image_bytes(img_resp.content, output_path):
                        logger.info(
                            f"[Cena #{scene_number}] Imagem real IA gerada via HF {sp['name']}: {output_path}"
                        )
                        return True
            except Exception as e:
                logger.debug(f"[Cena #{scene_number}] HF Space {sp['name']} indisponível: {e}")

    return False


async def _try_aihorde_image(
    prompt: str,
    output_path: str,
    scene_number: int,
    timeout: float = 42.0,
    visual_bible: Optional[Dict[str, str]] = None,
    story_seed: int = 424242,
) -> bool:
    """
    Provedor Principal Flux 9:16 (Sem Rate-Limit de IP): Gera imagem real em proporção
    nativa 9:16 (576x1024 -> 1080x1920) usando o modelo `Flux.1-Schnell fp8 (Compact)`
    no AI Horde (steps=4, cfg_scale=1.0, queue_position=0, 7 workers ativos), garantindo
    que todas as 20 cenas sejam geradas pelo mesmo motor Flux sem distorção vertical.
    """
    if os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") == "1":
        return False

    styled_prompt = _build_styled_prompt(prompt, visual_bible=visual_bible)
    api_key = (os.getenv("AIHORDE_API_KEY") or "0000000000").strip()
    headers = {
        "apikey": api_key,
        "Client-Agent": "ABVOS:2.0:admin",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": styled_prompt,
        "models": [
            "Flux.1-Schnell fp8 (Compact)",
        ],
        "params": {
            "width": 576,
            "height": 1024,
            "steps": 4,
            "n": 1,
            "sampler_name": "k_euler",
            "cfg_scale": 1.0,
            "seed": str(int(story_seed) + scene_number),
        },
        "nsfw": False,
        "censor_nsfw": False,
        "r2": True,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            sub = await client.post(
                "https://stablehorde.net/api/v2/generate/async",
                headers=headers,
                json=payload,
            )
            if sub.status_code != 202:
                logger.warning(f"[Cena #{scene_number}] AI Horde Flux recusou submissão ({sub.status_code}): {sub.text[:160]}")
                return False

            job_id = sub.json().get("id")
            if not job_id:
                return False

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                await asyncio.sleep(2.0)
                st = await client.get(
                    f"https://stablehorde.net/api/v2/generate/status/{job_id}",
                    headers=headers,
                )
                if st.status_code != 200:
                    continue
                st_data = st.json()
                if st_data.get("faulted"):
                    break
                if st_data.get("done"):
                    gens = st_data.get("generations") or []
                    if gens:
                        img_ref = gens[0].get("img")
                        if img_ref:
                            if img_ref.startswith("http"):
                                r_img = await client.get(img_ref)
                                raw_bytes = r_img.content if r_img.status_code == 200 else b""
                            else:
                                raw_bytes = base64.b64decode(img_ref)
                            if _save_and_normalize_image_bytes(raw_bytes, output_path):
                                logger.info(
                                    f"[Cena #{scene_number}] Imagem real 9:16 gerada via Flux.1-Schnell (AI Horde): {output_path}"
                                )
                                return True
                    break
    except Exception as e:
        logger.warning(f"[Cena #{scene_number}] Erro ao consultar AI Horde Flux: {e}")

    return False


async def _try_pollinations_flux_image(
    prompt: str,
    output_path: str,
    scene_number: int,
    timeout: float = 35.0,
    wait_on_rate_limit: bool = False,
    visual_bible: Optional[Dict[str, str]] = None,
    story_seed: int = 424242,
) -> bool:
    """
    Provedor Secundário Flux: Solicita imagem em proporção nativa 1:1 (1024x1024) ao
    Pollinations Flux (evitando o bug do servidor do Pollinations que estica imagens 1:1
    quando width != height) e compõe em 1080x1920 sem distorção via `_compose_square_to_9x16_seamless`.
    """
    global _POLLINATIONS_NEXT_AVAILABLE_AT

    if os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") == "1":
        return False

    now = time.monotonic()
    if now < _POLLINATIONS_NEXT_AVAILABLE_AT:
        remaining = _POLLINATIONS_NEXT_AVAILABLE_AT - now
        if not wait_on_rate_limit and remaining > 2.5:
            return False
        wait_s = min(remaining + 1.0, 48.0)
        if wait_s > 0.2:
            logger.info(f"[Cena #{scene_number}] Aguardando janela de {wait_s:.1f}s do Pollinations Flux...")
            await asyncio.sleep(wait_s)

    styled_prompt = _build_styled_prompt(prompt, visual_bible=visual_bible)
    encoded = quote(styled_prompt)
    seed = int(story_seed) + scene_number

    urls_to_try = [
        f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&nologo=true&enhance=false&seed={seed}",
    ]

    headers = {
        "User-Agent": "ABVOS-MediaEngine/2.0 (https://spirandeliempire.tech)",
        "Accept": "image/jpeg,image/png,image/*;q=0.8",
    }

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        for attempt, url in enumerate(urls_to_try, start=1):
            try:
                resp = await client.get(url)
                ctype = resp.headers.get("content-type", "").lower()
                if resp.status_code == 200 and ("image" in ctype or len(resp.content) > 10240):
                    if _save_and_normalize_image_bytes(resp.content, output_path, trim_bottom_watermark=True):
                        _POLLINATIONS_NEXT_AVAILABLE_AT = time.monotonic() + 45.5
                        logger.info(
                            f"[Cena #{scene_number}] Imagem real IA gerada via Pollinations Flux 1:1->9:16 (seed={seed}): {output_path}"
                        )
                        return True

                if resp.status_code in (402, 429):
                    retry_s = 45.0
                    m = re.search(r"Retry after\s+(\d+)\s*s", resp.text, re.IGNORECASE)
                    if m:
                        retry_s = min(float(m.group(1)) + 2.0, 48.0)
                    _POLLINATIONS_NEXT_AVAILABLE_AT = time.monotonic() + retry_s
                    if wait_on_rate_limit and attempt == 1:
                        logger.info(
                            f"[Cena #{scene_number}] Rate-limit Pollinations detectado ({retry_s:.1f}s). Aguardando janela completa..."
                        )
                        await asyncio.sleep(retry_s)
                        resp_retry = await client.get(url)
                        ctype_retry = resp_retry.headers.get("content-type", "").lower()
                        if resp_retry.status_code == 200 and ("image" in ctype_retry or len(resp_retry.content) > 10240):
                            if _save_and_normalize_image_bytes(resp_retry.content, output_path, trim_bottom_watermark=True):
                                _POLLINATIONS_NEXT_AVAILABLE_AT = time.monotonic() + 45.5
                                logger.info(
                                    f"[Cena #{scene_number}] Imagem real IA gerada via Pollinations Flux após aguardar janela: {output_path}"
                                )
                                return True
                    break
            except Exception as e:
                logger.warning(f"[Cena #{scene_number}] Tentativa {attempt} no provedor Pollinations falhou: {e}")
                await asyncio.sleep(0.8)

    return False


async def generate_scene_image_detailed(
    prompt: str,
    output_path: str,
    gemini_key: Optional[str] = None,
    scene_number: int = 1,
    title: str = "",
    max_retries: int = 2,
    timeout_per_attempt: float = 35.0,
    visual_bible: Optional[Dict[str, str]] = None,
    story_seed: int = 424242,
    include_character: bool = True,
    prefer_gemini_only: bool = False,
) -> Dict[str, Any]:
    """
    Gera imagem de cena real 9:16 (1080x1920) priorizando Google Gemini (Imagen 3 / Gemini Flash Image)
    e retornando metadados de provedor usado para auditoria do VideoSceneAgent.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    clean_key = (gemini_key or os.getenv("GEMINI_API_KEY", "")).strip()

    if os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") != "1":
        # 1. Google GenAI (provedor principal configurado pelo usuário)
        if clean_key:
            if await _try_google_genai_image(
                prompt=prompt,
                output_path=output_path,
                api_key=clean_key,
                scene_number=scene_number,
                timeout=timeout_per_attempt,
                visual_bible=visual_bible,
                include_character=include_character,
                max_attempts=max(2, max_retries),
            ):
                return {"path": output_path, "provider": "google_gemini", "fallback": False}

        if not prefer_gemini_only:
            # 2. AI Horde Flux.1-Schnell fp8 (Compact) nativo em 576x1024
            if await _try_aihorde_image(
                prompt=prompt,
                output_path=output_path,
                scene_number=scene_number,
                timeout=42.0,
                visual_bible=visual_bible,
                story_seed=story_seed,
            ):
                return {"path": output_path, "provider": "aihorde_flux", "fallback": False}

            # 3. Pollinations Flux 1024x1024 imediato
            if await _try_pollinations_flux_image(
                prompt=prompt,
                output_path=output_path,
                scene_number=scene_number,
                timeout=timeout_per_attempt,
                wait_on_rate_limit=False,
                visual_bible=visual_bible,
                story_seed=story_seed,
            ):
                return {"path": output_path, "provider": "pollinations_flux", "fallback": False}

            # 4. HuggingFace Gradio Spaces
            if await _try_hf_gradio_flux_image(
                prompt=prompt,
                output_path=output_path,
                scene_number=scene_number,
                timeout=25.0,
                visual_bible=visual_bible,
                story_seed=story_seed,
            ):
                return {"path": output_path, "provider": "hf_gradio_flux", "fallback": False}

            # 5. Pollinations Flux aguardando janela se necessário
            if await _try_pollinations_flux_image(
                prompt=prompt,
                output_path=output_path,
                scene_number=scene_number,
                timeout=35.0,
                wait_on_rate_limit=True,
                visual_bible=visual_bible,
                story_seed=story_seed,
            ):
                return {"path": output_path, "provider": "pollinations_flux", "fallback": False}

    # 6. Fallback offline (testes sem internet ou falha total de API)
    logger.info(f"[Cena #{scene_number}] Gerando arte visual offline de segurança (sem texto sobreposto).")
    fallback_img = create_cinematic_dark_backdrop(
        width=1080,
        height=1920,
        scene_number=scene_number,
        title=title or f"Cena {scene_number}",
        prompt=prompt,
    )
    fallback_img.save(output_path, "JPEG", quality=92)
    return {"path": output_path, "provider": "offline_backdrop", "fallback": True}


async def generate_single_scene_image_with_retry(
    prompt: str,
    output_path: str,
    gemini_key: Optional[str] = None,
    scene_number: int = 1,
    title: str = "",
    max_retries: int = 2,
    timeout_per_attempt: float = 25.0,
    visual_bible: Optional[Dict[str, str]] = None,
    story_seed: int = 424242,
) -> str:
    """
    Wrapper retrocompatível que retorna o caminho do arquivo salvo.
    """
    res = await generate_scene_image_detailed(
        prompt=prompt,
        output_path=output_path,
        gemini_key=gemini_key,
        scene_number=scene_number,
        title=title,
        max_retries=max_retries,
        timeout_per_attempt=timeout_per_attempt,
        visual_bible=visual_bible,
        story_seed=story_seed,
    )
    return res["path"]


async def generate_single_scene_image(
    prompt: str,
    output_path: str,
    gemini_key: Optional[str] = None,
    scene_number: int = 1,
    visual_bible: Optional[Dict[str, str]] = None,
    story_seed: int = 424242,
) -> str:
    """
    Gera a imagem de uma cena individual em proporção 9:16 (1080x1920).
    """
    return await generate_single_scene_image_with_retry(
        prompt=prompt,
        output_path=output_path,
        gemini_key=gemini_key,
        scene_number=scene_number,
        max_retries=2,
        visual_bible=visual_bible,
        story_seed=story_seed,
    )


async def generate_all_scene_images(
    scenes: List[Dict[str, Any]],
    output_dir: Path,
    gemini_key: Optional[str] = None,
    progress_callback: Optional[Any] = None,
    sequential: bool = True,
    visual_bible: Optional[Dict[str, str]] = None,
    story_seed: Optional[int] = None,
) -> List[str]:
    """
    Gera as 20 cenas do vídeo garantindo que todas recebam ilustrações reais conectadas
    à mesma história (mesmo protagonista, mesmo universo, mesma paleta e mesmo motor visual)
    e reportando progresso em tempo real ao banco de dados.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: List[str] = []
    total_scenes = len(scenes)

    if story_seed is None:
        seed_basis = json.dumps(visual_bible or {}, sort_keys=True) + (scenes[0].get("narration", "") if scenes else "")
        story_seed = 100000 + (abs(hash(seed_basis)) % 800000)

    for idx, sc in enumerate(scenes):
        scene_number = idx + 1
        prompt = (
            sc.get("visual_prompt")
            or sc.get("b_roll_description")
            or sc.get("narration")
            or f"Cinematic dark epic anime scene #{scene_number}, dramatic volumetric lighting, 8k"
        )
        sc_bible = sc.get("visual_bible") or visual_bible
        title = sc.get("on_screen_text") or sc.get("title") or sc.get("narration") or f"Cena {scene_number}"
        filename = f"scene_{scene_number:02d}.jpg"
        target_file = str(output_dir / filename)

        saved_path = await generate_single_scene_image_with_retry(
            prompt=prompt,
            output_path=target_file,
            gemini_key=gemini_key,
            scene_number=scene_number,
            title=title,
            max_retries=2,
            timeout_per_attempt=25.0,
            visual_bible=sc_bible,
            story_seed=story_seed,
        )
        generated_paths.append(saved_path)

        if progress_callback:
            try:
                res = progress_callback(scene_number, total_scenes)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as cb_err:
                logger.warning(f"Erro não-bloqueante no callback de progresso de cena: {cb_err}")

    return generated_paths
