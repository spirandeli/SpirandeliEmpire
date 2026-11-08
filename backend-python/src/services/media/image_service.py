import asyncio
import io
import logging
import math
import os
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import httpx
from google import genai
from google.genai import types

logger = logging.getLogger("abvos.media.images")


def create_cinematic_dark_backdrop(
    width: int = 1080,
    height: int = 1920,
    scene_number: int = 1,
    title: str = "",
    theme_color: str = "#0f172a",
) -> Image.Image:
    """
    Cria uma imagem de alta definição estilizada (9:16) com estética dark cinema,
    gradientes radiais volumétricos, iluminação de contraste e vinhetas cinematográficas.
    Usado como fallback ultra-estável ou composição visual de alta retenção.
    """
    base = Image.new("RGB", (width, height), color="#020617")
    draw = ImageDraw.Draw(base)

    # Cores dramáticas neo-noir / dark anime
    palettes = [
        ((15, 23, 42), (88, 28, 135), (220, 38, 38)),   # Dark Indigo & Crimson
        ((8, 47, 73), (12, 74, 110), (2, 132, 199)),    # Midnight Oceanic
        ((24, 24, 27), (69, 10, 10), (245, 158, 11)),   # Obsidian & Amber
        ((15, 23, 42), (4, 120, 87), (16, 185, 129)),   # Shadow Emerald
    ]
    c1, c2, c3 = palettes[scene_number % len(palettes)]

    # Gradiente vertical dramático
    for y in range(height):
        factor = y / height
        if factor < 0.5:
            inter_factor = factor * 2.0
            r = int(c1[0] * (1 - inter_factor) + c2[0] * inter_factor)
            g = int(c1[1] * (1 - inter_factor) + c2[1] * inter_factor)
            b = int(c1[2] * (1 - inter_factor) + c2[2] * inter_factor)
        else:
            inter_factor = (factor - 0.5) * 2.0
            r = int(c2[0] * (1 - inter_factor) + c3[0] * inter_factor)
            g = int(c2[1] * (1 - inter_factor) + c3[1] * inter_factor)
            b = int(c2[2] * (1 - inter_factor) + c3[2] * inter_factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Luz volumétrica central (feixe de holofote sutil)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    cx = width // 2
    cy = int(height * 0.45)
    for radius in range(550, 40, -40):
        alpha = int(45 * (1 - radius / 550))
        overlay_draw.ellipse(
            [cx - radius, cy - int(radius * 1.4), cx + radius, cy + int(radius * 1.4)],
            fill=(255, 255, 255, alpha),
        )

    # Brilho de partículas / poeira cósmica
    random.seed(scene_number * 100)
    for _ in range(80):
        px = random.randint(40, width - 40)
        py = random.randint(100, height - 100)
        p_rad = random.randint(2, 6)
        p_alpha = random.randint(60, 180)
        overlay_draw.ellipse(
            [px - p_rad, py - p_rad, px + p_rad, py + p_rad],
            fill=(255, 230, 150, p_alpha),
        )

    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    base = base.filter(ImageFilter.GaussianBlur(radius=1.5))

    # Vinheta pesada nas bordas para estética Dark Short
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vignette_draw = ImageDraw.Draw(vignette)
    for r in range(0, 150):
        v_alpha = int(180 * (1 - r / 150))
        vignette_draw.rectangle([r, r, width - r, height - r], outline=(0, 0, 0, v_alpha), width=2)
    base = Image.alpha_composite(base.convert("RGBA"), vignette).convert("RGB")

    return base


async def generate_single_scene_image(
    prompt: str,
    output_path: str,
    gemini_key: Optional[str] = None,
    scene_number: int = 1,
) -> str:
    """
    Gera a imagem de uma cena individual em proporção 9:16 (1080x1920).
    Tenta primeiro o Google Imagen 3 com a chave API do usuário/projeto;
    se não estiver disponível ou falhar por cota, aplica o fallback estilizado neo-noir.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    clean_key = (gemini_key or os.getenv("GEMINI_API_KEY", "")).strip()

    # Tentativa com Google Imagen 3
    if clean_key:
        try:
            client = genai.Client(api_key=clean_key)
            # Reforça atmosfera Dark Epic Anime 9:16
            enhanced_prompt = f"{prompt}, dark epic anime aesthetic, cinematic lighting, 8k resolution, ultra detailed, dramatic atmosphere"

            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: client.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="9:16",
                        output_mime_type="image/jpeg",
                    ),
                ),
            )
            if resp.generated_images and resp.generated_images[0].image.image_bytes:
                img_bytes = resp.generated_images[0].image.image_bytes
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                logger.info(f"Cena #{scene_number} gerada com sucesso via Google Imagen 3: {output_path}")
                return output_path
        except Exception as e:
            logger.warning(f"Google Imagen 3 indisponível para cena #{scene_number} ({e}). Ativando fallback estilizado.")

    # Fallback Cinemático
    fallback_img = create_cinematic_dark_backdrop(width=1080, height=1920, scene_number=scene_number)
    fallback_img.save(output_path, "JPEG", quality=92)
    logger.info(f"Cena #{scene_number} salva via motor visual cinemático: {output_path}")
    return output_path


async def generate_all_scene_images(
    scenes: List[Dict[str, Any]],
    output_dir: Path,
    gemini_key: Optional[str] = None,
) -> List[str]:
    """
    Gera as imagens para todas as cenas com controle de concorrência.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(2)  # Limite de 2 chamadas concorrentes para respeitar rate-limit

    async def _worker(idx: int, sc: Dict[str, Any]) -> str:
        prompt = sc.get("visual_prompt") or sc.get("b_roll_description") or "Cinematic mysterious scene in total darkness, Unreal Engine 5"
        filename = f"scene_{idx + 1:02d}.jpg"
        target_file = str(output_dir / filename)
        async with semaphore:
            return await generate_single_scene_image(
                prompt=prompt,
                output_path=target_file,
                gemini_key=gemini_key,
                scene_number=idx + 1,
            )

    tasks = [_worker(i, sc) for i, sc in enumerate(scenes)]
    return await asyncio.gather(*tasks)

