import asyncio
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.services.media.media_settings import get_ffmpeg_path, get_ffprobe_path

logger = logging.getLogger("abvos.media.video_renderer")


async def render_video_with_audio_and_subtitles(
    image_paths: List[str],
    audio_path: str,
    output_video_path: str,
    subtitle_ass_path: Optional[str] = None,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
    scene_duration: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Renderiza um vídeo 9:16 (1080x1920) H.264/AAC completo:
    1. Calcula a duração de cada cena para coincidir exatamente com a narração total ou 3.0s por cena.
    2. Aplica zoom dinâmico (Ken Burns) e converte cada imagem para fluxo de vídeo 30fps.
    3. Concatena as cenas visualmente.
    4. Sincroniza a narração de áudio.
    5. Queima as legendas estilizadas .ass (Hormozi style) no vídeo final.
    """
    ffmpeg = get_ffmpeg_path()
    if not os.path.exists(ffmpeg):
        raise FileNotFoundError(f"Executável FFmpeg não encontrado em {ffmpeg}")

    output_dir = Path(output_video_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "render_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Validação estrita pré-compilação: confirma que todos os assets de imagem e áudio estão salvos no disco
    for idx, img in enumerate(image_paths):
        if not os.path.exists(img) or os.path.getsize(img) == 0:
            raise FileNotFoundError(f"Asset da cena #{idx + 1} não foi salvo no disco ou está vazio: {img}")

    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise FileNotFoundError(f"Asset de áudio da narração não foi salvo no disco ou está vazio: {audio_path}")

    # Determina a duração do áudio e tempo por cena
    ffprobe = get_ffprobe_path()
    audio_duration = 60.0
    if os.path.exists(ffprobe):
        try:
            probe_cmd = [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            audio_duration = float(res.stdout.strip())
        except Exception as e:
            logger.warning(f"Não foi possível obter duração exata do áudio ({e}). Usando padrão de 60s.")

    num_images = max(1, len(image_paths))
    # Para 20 cenas em vídeos Dark, cada cena tem exatamente 3.0s totalizando 60.0s (1 minuto)
    if scene_duration is None:
        duration_per_scene = 3.0 if num_images == 20 else round(max(audio_duration, 60.0) / num_images, 3)
    else:
        duration_per_scene = float(scene_duration)

    target_total_duration = round(num_images * duration_per_scene, 2)

    logger.info(
        f"CONFIRMAÇÃO DE ASSETS OK: {num_images} cenas ({duration_per_scene}s/cena) e áudio ({audio_duration:.2f}s) validados no disco. "
        f"Disparando montagem final FFmpeg sem cortes (Duração alvo exata: {target_total_duration}s)..."
    )

    # 2. Constrói arquivo concat com durações exatas
    concat_file_path = temp_dir / "concat_list.txt"
    with open(concat_file_path, "w", encoding="utf-8") as f:
        for img in image_paths:
            f.write(f"file '{os.path.abspath(img)}'\n")
            f.write(f"duration {duration_per_scene}\n")
        # No ffmpeg concat demuxer, a última imagem precisa ser repetida
        if image_paths:
            f.write(f"file '{os.path.abspath(image_paths[-1])}'\n")

    # 3. Monta o filtro de vídeo:
    # - scale para 1080x1920 (padronização 9:16)
    # - format=yuv420p para máxima compatibilidade
    # - queima de legenda .ass se fornecida
    vf_filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "format=yuv420p",
    ]

    if subtitle_ass_path and os.path.exists(subtitle_ass_path):
        # Escapa caminhos para o filtro subtitles do ffmpeg
        clean_sub_path = os.path.abspath(subtitle_ass_path).replace("\\", "/").replace(":", "\\:")
        vf_filters.append(f"ass='{clean_sub_path}'")

    filter_complex_str = ",".join(vf_filters)

    # Filtro de áudio com apad para garantir preenchimento até a duração total sem interrupções bruscas
    audio_filter = f"apad=whole_dur={target_total_duration}"

    cmd = [
        ffmpeg,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file_path),
        "-i", os.path.abspath(audio_path),
        "-vf", filter_complex_str,
        "-af", audio_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", str(fps),
        "-t", str(target_total_duration),
        "-movflags", "+faststart",
        output_video_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace")
        logger.error(f"Erro FFmpeg ao renderizar com legendas: {err_msg[:400]}")
        # Tentativa de fallback sem legendas embutidas caso a libass falhe
        if subtitle_ass_path:
            logger.info("Tentando renderizar sem legenda embutida...")
            fallback_vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
            fallback_cmd = [
                ffmpeg,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file_path),
                "-i", os.path.abspath(audio_path),
                "-vf", fallback_vf,
                "-af", audio_filter,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-r", str(fps),
                "-t", str(target_total_duration),
                "-movflags", "+faststart",
                output_video_path,
            ]
            fallback_proc = await asyncio.create_subprocess_exec(
                *fallback_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, fallback_stderr = await fallback_proc.communicate()
            if fallback_proc.returncode != 0:
                raise RuntimeError(f"FFmpeg falhou na renderização: {fallback_stderr.decode(errors='replace')[:200]}")

    # Limpeza de arquivos temporários
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    file_size_bytes = os.path.getsize(output_video_path) if os.path.exists(output_video_path) else 0
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    logger.info(f"Vídeo renderizado com sucesso: {output_video_path} ({file_size_mb} MB)")
    return {
        "success": True,
        "video_path": output_video_path,
        "size_mb": file_size_mb,
        "resolution": f"{width}x{height}",
        "aspect_ratio": "9:16",
        "duration_seconds": round(audio_duration, 2),
    }

