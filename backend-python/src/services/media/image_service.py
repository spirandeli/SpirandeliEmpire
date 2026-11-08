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


async def generate_single_scene_image_with_retry(
    prompt: str,
    output_path: str,
    gemini_key: Optional[str] = None,
    scene_number: int = 1,
    title: str = "",
    max_retries: int = 3,
    timeout_per_attempt: float = 25.0,
) -> str:
    """
    Gera imagem de cena com retry automático (3 tentativas por cena) e timeout por tentativa.
    Se a IA demorar ou falhar, ativa fallback instantâneo para a imagem de segurança
    cinematográfica neo-noir. Nenhuma cena pode ser suprimida por falha de API.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    clean_key = (gemini_key or os.getenv("GEMINI_API_KEY", "")).strip()

    if clean_key:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[Cena #{scene_number}] Tentativa {attempt}/{max_retries} de geração visual via IA...")

                async def _call_imagen():
                    client = genai.Client(api_key=clean_key)
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
                        with open(output_path, "wb") as f:
                            f.write(resp.generated_images[0].image.image_bytes)
                        return True
                    return False

                success = await asyncio.wait_for(_call_imagen(), timeout=timeout_per_attempt)
                if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"[Cena #{scene_number}] Imagem salva com sucesso via Google Imagen 3 (tentativa {attempt}): {output_path}")
                    return output_path
                else:
                    logger.warning(f"[Cena #{scene_number}] Tentativa {attempt}/{max_retries} não gerou arquivo válido.")
            except asyncio.TimeoutError:
                logger.warning(f"[Cena #{scene_number}] Timeout de {timeout_per_attempt}s atingido na tentativa {attempt}/{max_retries}.")
            except Exception as e:
                logger.warning(f"[Cena #{scene_number}] Erro na tentativa {attempt}/{max_retries}: {e}")

            if attempt < max_retries:
                await asyncio.sleep(1.0)

    # Fallback para Imagem de Segurança Cinematográfica
    logger.info(f"[Cena #{scene_number}] Ativando imagem de segurança cinematográfica ABVOS após {max_retries} tentativas.")
    fallback_img = create_cinematic_dark_backdrop(
        width=1080,
        height=1920,
        scene_number=scene_number,
        title=title or f"Cena {scene_number}",
    )
    fallback_img.save(output_path, "JPEG", quality=92)
    logger.info(f"[Cena #{scene_number}] Asset de segurança gravado e validado em disco: {output_path}")
    return output_path


async def generate_single_scene_image(
    prompt: str,
    output_path: str,
    gemini_key: Optional[str] = None,
    scene_number: int = 1,
) -> str:
    """
    Gera a imagem de uma cena individual em proporção 9:16 (1080x1920).
    Aplica retry automático de 3 tentativas e fallback seguro.
    """
    return await generate_single_scene_image_with_retry(
        prompt=prompt,
        output_path=output_path,
        gemini_key=gemini_key,
        scene_number=scene_number,
        max_retries=3,
    )


async def generate_all_scene_images(
    scenes: List[Dict[str, Any]],
    output_dir: Path,
    gemini_key: Optional[str] = None,
    progress_callback: Optional[Any] = None,
    sequential: bool = True,
) -> List[str]:
    """
    Execução Sequencial Garantida das cenas (iterando obrigatoriamente pelas 20 cenas).
    Nenhuma cena pode ser suprimida por falha de API: retry automático (3 tentativas)
    com fallback para imagem de segurança caso a IA demore a responder.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: List[str] = []
    total_scenes = len(scenes)

    for idx, sc in enumerate(scenes):
        scene_number = idx + 1
        prompt = sc.get("visual_prompt") or sc.get("b_roll_description") or f"Cinematic dark scene #{scene_number}, Unreal Engine 5"
        title = sc.get("on_screen_text") or sc.get("title") or f"Cena {scene_number}"
        filename = f"scene_{scene_number:02d}.jpg"
        target_file = str(output_dir / filename)

        saved_path = await generate_single_scene_image_with_retry(
            prompt=prompt,
            output_path=target_file,
            gemini_key=gemini_key,
            scene_number=scene_number,
            title=title,
            max_retries=3,
            timeout_per_attempt=25.0,
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

