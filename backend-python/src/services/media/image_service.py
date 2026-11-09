import asyncio
import io
import logging
import math
import os
import random
import textwrap
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import httpx
from google import genai
from google.genai import types

logger = logging.getLogger("abvos.media.images")

# Cache em memória para não repetir chamadas em modelos indisponíveis para a mesma chave
_UNAVAILABLE_IMAGEN_KEYS: set[str] = set()


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
    Cria uma composição visual 9:16 (1080x1920) rica com estética Dark Cinema:
    - Iluminação volumétrica, eclipse/portal celestial, silhueta arquitetônica/montanhosa em camadas,
      feixes de luz e partículas em brasa;
    - Quadro narrativo tipográfico com o título e contexto visual da cena.
    Usado apenas quando todas as APIs externas de IA estiverem offline.
    """
    base = Image.new("RGB", (width, height), color="#020617")
    draw = ImageDraw.Draw(base)

    palettes = [
        ((10, 15, 32), (68, 22, 115), (185, 28, 28), (251, 191, 36)),   # Dark Indigo, Crimson & Gold
        ((6, 32, 56), (14, 65, 98), (3, 105, 161), (56, 189, 248)),     # Abyssal Cyan & Ice
        ((18, 18, 22), (69, 10, 10), (180, 83, 9), (252, 211, 77)),     # Obsidian, Hellfire & Amber
        ((9, 20, 36), (6, 95, 70), (16, 185, 129), (167, 243, 208)),    # Shadow Emerald & Mystic Mint
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

    # 2. Feixes de luz celestial / eclipse central
    cx = width // 2
    cy = int(height * 0.36)
    random.seed(scene_number * 1337)

    # Raios de luz diagonais
    for i in range(12):
        angle = (i / 12.0) * math.pi * 2 + (scene_number * 0.25)
        x_end = cx + int(math.cos(angle) * 1100)
        y_end = cy + int(math.sin(angle) * 1100)
        overlay_draw.line([(cx, cy), (x_end, y_end)], fill=(*accent, 22), width=28)

    # Halo luminoso e eclipse
    for radius in range(460, 120, -25):
        alpha = int(55 * (1 - radius / 460))
        overlay_draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(*accent, alpha),
        )
    # Núcleo do eclipse sombrio com anel dourado/neon
    eclipse_r = 145
    overlay_draw.ellipse(
        [cx - eclipse_r - 6, cy - eclipse_r - 6, cx + eclipse_r + 6, cy + eclipse_r + 6],
        outline=(*accent, 210),
        width=6,
    )
    overlay_draw.ellipse(
        [cx - eclipse_r, cy - eclipse_r, cx + eclipse_r, cy + eclipse_r],
        fill=(8, 10, 20, 245),
    )

    # 3. Silhueta de montanhas / templos góticos no terço inferior
    for layer_idx, (base_y, amp, col_alpha) in enumerate([
        (int(height * 0.68), 110, (12, 16, 30, 190)),
        (int(height * 0.74), 85, (6, 9, 18, 230)),
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

    # 4. Partículas e brasas flutuantes
    for _ in range(95):
        px = random.randint(30, width - 30)
        py = random.randint(80, height - 120)
        p_rad = random.randint(2, 7)
        p_alpha = random.randint(70, 210)
        overlay_draw.ellipse(
            [px - p_rad, py - p_rad, px + p_rad, py + p_rad],
            fill=(*accent, p_alpha),
        )

    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    base = base.filter(ImageFilter.GaussianBlur(radius=1.0))

    # 5. Vinheta cinematográfica e tipografia da cena
    hud = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    hud_draw = ImageDraw.Draw(hud)

    for r in range(0, 120):
        v_alpha = int(170 * (1 - r / 120))
        hud_draw.rectangle([r, r, width - r, height - r], outline=(0, 0, 0, v_alpha), width=2)

    # Painel central translúcido para título e descrição da cena
    card_top = int(height * 0.52)
    card_bottom = int(height * 0.74)
    hud_draw.rounded_rectangle(
        [70, card_top, width - 70, card_bottom],
        radius=28,
        fill=(5, 8, 20, 185),
        outline=(*accent, 130),
        width=3,
    )

    badge_font = _load_font(28, bold=True)
    title_font = _load_font(44, bold=True)
    desc_font = _load_font(28, bold=False)

    badge_text = f"CENA {scene_number:02d} • DARK CINEMA"
    hud_draw.text((width // 2, card_top + 48), badge_text, fill=(*accent, 255), font=badge_font, anchor="mm")

    clean_title = (title or f"Cena {scene_number}").strip().upper()
    wrapped_title = textwrap.wrap(clean_title, width=22)[:2]
    curr_y = card_top + 115
    for line in wrapped_title:
        hud_draw.text((width // 2, curr_y), line, fill=(255, 255, 255, 255), font=title_font, anchor="mm")
        curr_y += 54

    if prompt:
        clean_prompt = prompt.split("--ar")[0].strip()
        wrapped_desc = textwrap.wrap(clean_prompt, width=38)[:3]
        curr_y += 18
        for line in wrapped_desc:
            hud_draw.text((width // 2, curr_y), line, fill=(203, 213, 225, 230), font=desc_font, anchor="mm")
            curr_y += 38

    base = Image.alpha_composite(base.convert("RGBA"), hud).convert("RGB")
    return base


def _save_and_normalize_image_bytes(
    raw_bytes: bytes,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    trim_bottom_watermark: bool = False,
) -> bool:
    """
    Valida se os bytes recebidos são uma imagem real íntegra, remove eventuais marcas d'água
    de rodapé com crop proporcional e grava em 1080x1920 (9:16) com alta qualidade JPEG.
    """
    if not raw_bytes or len(raw_bytes) < 2048:
        return False
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            rgb = img.convert("RGB")
            if trim_bottom_watermark:
                iw, ih = rgb.size
                # Remove 5% da borda inferior e 2.5% das laterais para manter proporção 9:16 limpa
                crop_x = int(iw * 0.025)
                crop_bottom = int(ih * 0.95)
                rgb = rgb.crop((crop_x, 0, iw - crop_x, crop_bottom))
            if rgb.size != (width, height):
                rgb = rgb.resize((width, height), Image.Resampling.LANCZOS)
            rgb.save(output_path, "JPEG", quality=92)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 2048
    except Exception as e:
        logger.warning(f"Falha ao validar/normalizar imagem recebida: {e}")
        return False


async def _try_google_genai_image(
    prompt: str,
    output_path: str,
    api_key: str,
    scene_number: int,
    timeout: float = 20.0,
) -> bool:
    """
    Provedor 1: Tenta gerar imagem 9:16 via Google GenAI (gemini-3.1-flash-image / gemini-2.5-flash-image).
    """
    if not api_key or api_key in _UNAVAILABLE_IMAGEN_KEYS:
        return False

    enhanced_prompt = (
        f"Generate a vertical 9:16 dark epic cinematic illustration: {prompt}. "
        "Dramatic volumetric lighting, hyper-detailed, 8k resolution, no text or watermarks."
    )

    def _sync_call() -> Optional[bytes]:
        client = genai.Client(api_key=api_key)
        for model_name in ("gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3.1-flash-lite-image"):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=enhanced_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )
                for cand in getattr(resp, "candidates", []) or []:
                    for part in getattr(cand.content, "parts", []) or []:
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            return inline.data
            except Exception as ex:
                err_str = str(ex).lower()
                if any(k in err_str for k in ("429", "resource_exhausted", "quota", "404", "not_found", "403", "billing")):
                    continue
                raise ex
        return None

    try:
        loop = asyncio.get_running_loop()
        img_bytes = await asyncio.wait_for(loop.run_in_executor(None, _sync_call), timeout=timeout)
        if img_bytes and _save_and_normalize_image_bytes(img_bytes, output_path):
            logger.info(f"[Cena #{scene_number}] Imagem real gerada via Google GenAI: {output_path}")
            return True
        # Se retornou None para ambos os modelos, marca chave para não atrasar as próximas cenas
        _UNAVAILABLE_IMAGEN_KEYS.add(api_key)
    except Exception as e:
        logger.warning(f"[Cena #{scene_number}] Google GenAI Image indisponível ({e}), alternando para provedor Flux...")
        _UNAVAILABLE_IMAGEN_KEYS.add(api_key)

    return False


async def _try_pollinations_flux_image(
    prompt: str,
    output_path: str,
    scene_number: int,
    timeout: float = 25.0,
) -> bool:
    """
    Provedor 2: Gera imagem real de IA em proporção 9:16 (1080x1920) usando Pollinations.ai (Flux),
    garantindo cenas reais ilustradas mesmo quando a chave Gemini não possui Imagen pago.
    """
    if os.getenv("ABVOS_DISABLE_EXTERNAL_IMAGE_API") == "1":
        return False

    clean_prompt = prompt.replace("\n", " ").strip()[:380]
    styled_prompt = (
        f"{clean_prompt}, dark cinematic epic style, dramatic chiaroscuro lighting, "
        "ultra detailed masterpiece, vertical 9:16 composition"
    )
    encoded = quote(styled_prompt)
    seed = (scene_number * 7919) + random.randint(100, 9999)

    urls_to_try = [
        f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&model=flux&nologo=true&seed={seed}",
        f"https://image.pollinations.ai/prompt/{encoded}?width=720&height=1280&nologo=true&seed={seed}",
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
                        logger.info(
                            f"[Cena #{scene_number}] Imagem real IA gerada via Flux (tentativa {attempt}): {output_path}"
                        )
                        return True
            except Exception as e:
                logger.warning(f"[Cena #{scene_number}] Tentativa {attempt} no provedor Flux falhou: {e}")
                await asyncio.sleep(0.8)

    return False


async def generate_single_scene_image_with_retry(
    prompt: str,
    output_path: str,
    gemini_key: Optional[str] = None,
    scene_number: int = 1,
    title: str = "",
    max_retries: int = 2,
    timeout_per_attempt: float = 22.0,
) -> str:
    """
    Gera imagem de cena real 9:16 (1080x1920) utilizando arquitetura Multi-Provider:
    1. Google GenAI (Imagen 3 / Gemini 2.0 Image Generation)
    2. Pollinations.ai (Flux 9:16 Real AI Image Generation)
    3. Fallback Cinematográfico com arte procedural e tipografia da cena (caso offline)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    clean_key = (gemini_key or os.getenv("GEMINI_API_KEY", "")).strip()

    # 1. Tenta Google GenAI (se houver chave válida)
    if clean_key:
        if await _try_google_genai_image(
            prompt=prompt,
            output_path=output_path,
            api_key=clean_key,
            scene_number=scene_number,
            timeout=timeout_per_attempt,
        ):
            return output_path

    # 2. Tenta Pollinations Flux (Geração Real de Imagem IA 9:16)
    for attempt in range(1, max_retries + 1):
        if await _try_pollinations_flux_image(
            prompt=prompt,
            output_path=output_path,
            scene_number=scene_number,
            timeout=timeout_per_attempt,
        ):
            return output_path
        if attempt < max_retries:
            await asyncio.sleep(1.0)

    # 3. Fallback offline com composição visual e tipografia da cena
    logger.info(f"[Cena #{scene_number}] Gerando composição visual cinematográfica local com tipografia.")
    fallback_img = create_cinematic_dark_backdrop(
        width=1080,
        height=1920,
        scene_number=scene_number,
        title=title or f"Cena {scene_number}",
        prompt=prompt,
    )
    fallback_img.save(output_path, "JPEG", quality=92)
    return output_path


async def generate_single_scene_image(
    prompt: str,
    output_path: str,
    gemini_key: Optional[str] = None,
    scene_number: int = 1,
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
    )


async def generate_all_scene_images(
    scenes: List[Dict[str, Any]],
    output_dir: Path,
    gemini_key: Optional[str] = None,
    progress_callback: Optional[Any] = None,
    sequential: bool = True,
) -> List[str]:
    """
    Gera as 20 cenas do vídeo garantindo que nenhuma cena seja suprimida e reportando
    progresso ao banco de dados para atualização em tempo real no Kanban e Storage Viewer.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: List[str] = []
    total_scenes = len(scenes)

    for idx, sc in enumerate(scenes):
        scene_number = idx + 1
        prompt = (
            sc.get("visual_prompt")
            or sc.get("b_roll_description")
            or f"Cinematic dark epic scene #{scene_number}, dramatic lighting, 8k"
        )
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
            timeout_per_attempt=20.0,
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
