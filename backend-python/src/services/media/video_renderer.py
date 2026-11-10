import asyncio
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.services.media.media_settings import get_ffmpeg_path, get_ffprobe_path

logger = logging.getLogger("abvos.media.video_renderer")

VALID_CAMERA_MOTIONS = ("zoom_in", "zoom_out", "pan_left", "pan_right", "tilt_up")


def _probe_media_file(media_path: str) -> Dict[str, Any]:
    """Inspeciona streams de vídeo/áudio e duração exata usando ffprobe."""
    ffprobe = get_ffprobe_path()
    if not os.path.exists(ffprobe):
        return {}
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-of", "json",
        media_path,
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return json.loads(res.stdout or "{}")
    except Exception as e:
        logger.warning(f"Erro ao inspecionar mídia via ffprobe ({media_path}): {e}")
        return {}


def _zoompan_expr_for_motion(motion: str, frames: int, width: int, height: int, fps: int) -> str:
    """
    Constrói filtro Ken Burns suave (zoompan) em 30fps para dar movimento cinematográfico
    sem tremor e sem cortes bruscos.
    """
    frames = max(15, int(frames))
    m = (motion or "zoom_in").lower().strip()
    # Escala prévia 1.25x para evitar serrilhado e dar margem limpa de pan/zoom
    pre_w = int(width * 1.25)
    pre_h = int(height * 1.25)
    base_scale = f"scale={pre_w}:{pre_h}:force_original_aspect_ratio=increase,crop={pre_w}:{pre_h},setsar=1"

    if m == "zoom_out":
        zp = (
            f"zoompan=z='max(1.0,1.14-0.14*(on/{frames}))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={width}x{height}:fps={fps}"
        )
    elif m == "pan_left":
        zp = (
            f"zoompan=z='1.12':"
            f"x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={width}x{height}:fps={fps}"
        )
    elif m == "pan_right":
        zp = (
            f"zoompan=z='1.12':"
            f"x='(iw-iw/zoom)*(on/{frames})':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={width}x{height}:fps={fps}"
        )
    elif m == "tilt_up":
        zp = (
            f"zoompan=z='1.12':"
            f"x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(1-on/{frames})':"
            f"d={frames}:s={width}x{height}:fps={fps}"
        )
    else:  # zoom_in padrão
        zp = (
            f"zoompan=z='min(1.14,1.0+0.14*(on/{frames}))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={width}x{height}:fps={fps}"
        )
    return f"{base_scale},{zp}"


async def _render_single_motion_clip(
    ffmpeg: str,
    image_path: str,
    clip_path: str,
    duration: float,
    motion: str,
    width: int,
    height: int,
    fps: int,
) -> bool:
    """Renderiza uma única cena com efeito Ken Burns para posterior concatenação com xfade."""
    frames = max(15, int(round(duration * fps)))
    vf = f"{_zoompan_expr_for_motion(motion, frames, width, height, fps)},format=yuv420p"
    cmd = [
        ffmpeg,
        "-y",
        "-i", os.path.abspath(image_path),
        "-vf", vf,
        "-t", f"{duration:.3f}",
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-an",
        clip_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.warning(f"Falha ao renderizar clip Ken Burns ({motion}): {stderr.decode(errors='replace')[:200]}")
        return False
    return os.path.exists(clip_path) and os.path.getsize(clip_path) > 0


async def render_video_with_audio_and_subtitles(
    image_paths: List[str],
    audio_path: str,
    output_video_path: str,
    subtitle_ass_path: Optional[str] = None,
    fps: int = 30,
    width: int = 1080,
    height: int = 1920,
    scene_duration: Optional[float] = None,
    scene_durations: Optional[List[float]] = None,
    camera_motions: Optional[List[str]] = None,
    enable_motion: bool = True,
    transition_duration: float = 0.22,
    normalize_audio: bool = True,
) -> Dict[str, Any]:
    """
    Renderiza um vídeo 9:16 (1080x1920) H.264/AAC completo:
    1. Calcula a duração individual de cada cena para coincidir com a frase falada.
    2. Quando `enable_motion=True`, aplica movimento de câmera Ken Burns por cena e transições
       suaves `xfade` entre cenas (com fallback seguro para concat estático se necessário).
    3. Sincroniza a narração de áudio (opcionalmente normalizada via loudnorm) sem BGM.
    4. Queima as legendas estilizadas .ass a 30fps e audita o MP4 final via ffprobe.
    """
    ffmpeg = get_ffmpeg_path()
    if not os.path.exists(ffmpeg):
        raise FileNotFoundError(f"Executável FFmpeg não encontrado em {ffmpeg}")

    output_dir = Path(output_video_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "render_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Validação estrita pré-compilação
    for idx, img in enumerate(image_paths):
        if not os.path.exists(img) or os.path.getsize(img) == 0:
            raise FileNotFoundError(f"Asset da cena #{idx + 1} não foi salvo no disco ou está vazio: {img}")

    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        raise FileNotFoundError(f"Asset de áudio da narração não foi salvo no disco ou está vazio: {audio_path}")

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
    if scene_durations and len(scene_durations) == num_images:
        per_scene_durs = [round(max(0.6, float(d)), 2) for d in scene_durations]
        target_total_duration = round(sum(per_scene_durs), 2)
    else:
        if scene_duration is None:
            duration_per_scene = 3.0 if num_images == 20 else round(max(audio_duration, 10.0) / num_images, 3)
        else:
            duration_per_scene = float(scene_duration)
        per_scene_durs = [duration_per_scene for _ in range(num_images)]
        target_total_duration = round(num_images * duration_per_scene, 2)

    # Garante que o vídeo não corte o final do áudio caso o áudio seja ligeiramente maior
    if audio_duration > target_total_duration:
        diff = round(audio_duration - target_total_duration + 0.25, 2)
        per_scene_durs[-1] = round(per_scene_durs[-1] + diff, 2)
        target_total_duration = round(sum(per_scene_durs), 2)

    motions = [
        (camera_motions[i] if camera_motions and i < len(camera_motions) else VALID_CAMERA_MOTIONS[i % len(VALID_CAMERA_MOTIONS)])
        for i in range(num_images)
    ]

    logger.info(
        f"CONFIRMAÇÃO DE ASSETS OK: {num_images} cenas e áudio ({audio_duration:.2f}s) validados. "
        f"Renderizando vídeo {width}x{height}@{fps}fps (motion={enable_motion}, duração={target_total_duration}s)..."
    )

    clean_sub_path = (
        os.path.abspath(subtitle_ass_path).replace("\\", "/").replace(":", "\\:")
        if (subtitle_ass_path and os.path.exists(subtitle_ass_path))
        else None
    )
    audio_filter = (
        f"loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur={target_total_duration}"
        if normalize_audio
        else f"apad=whole_dur={target_total_duration}"
    )

    rendered_ok = False

    # 2A. Modo Cinematográfico (Ken Burns + xfade suave entre cenas)
    if enable_motion and num_images >= 1:
        try:
            fade_dur = min(transition_duration, min(per_scene_durs) * 0.35) if num_images > 1 else 0.0
            clip_paths: List[str] = []
            clip_durs: List[float] = []
            for idx, (img, dur, mot) in enumerate(zip(image_paths, per_scene_durs, motions)):
                # Cada cena exceto a última ganha +fade_dur para que a soma após xfade bata exatamente em target_total_duration
                clip_d = round(dur + (fade_dur if idx < num_images - 1 else 0.0), 3)
                c_path = str(temp_dir / f"clip_{idx + 1:02d}.mp4")
                ok = await _render_single_motion_clip(
                    ffmpeg=ffmpeg,
                    image_path=img,
                    clip_path=c_path,
                    duration=clip_d,
                    motion=mot,
                    width=width,
                    height=height,
                    fps=fps,
                )
                if not ok:
                    clip_paths = []
                    break
                clip_paths.append(c_path)
                clip_durs.append(clip_d)

            if clip_paths and len(clip_paths) == num_images:
                input_args: List[str] = []
                for cp in clip_paths:
                    input_args.extend(["-i", cp])
                input_args.extend(["-i", os.path.abspath(audio_path)])
                audio_input_idx = len(clip_paths)

                filter_parts: List[str] = []
                if num_images == 1:
                    last_v = "[0:v]"
                else:
                    prev_label = "[0:v]"
                    acc_offset = 0.0
                    for idx in range(num_images - 1):
                        acc_offset = round(acc_offset + per_scene_durs[idx], 3)
                        out_label = f"[vx{idx}]"
                        filter_parts.append(
                            f"{prev_label}[{idx + 1}:v]xfade=transition=fade:duration={fade_dur:.3f}:offset={acc_offset:.3f}{out_label}"
                        )
                        prev_label = out_label
                    last_v = prev_label

                v_chain = ["format=yuv420p"]
                if clean_sub_path:
                    v_chain.append(f"ass='{clean_sub_path}'")
                filter_parts.append(f"{last_v}{','.join(v_chain)}[vout]")
                filter_parts.append(f"[{audio_input_idx}:a]{audio_filter}[aout]")

                cmd_motion = [
                    ffmpeg,
                    "-y",
                    *input_args,
                    "-filter_complex", ";".join(filter_parts),
                    "-map", "[vout]",
                    "-map", "[aout]",
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "22",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-r", str(fps),
                    "-t", str(target_total_duration),
                    "-movflags", "+faststart",
                    output_video_path,
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd_motion,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                if proc.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
                    rendered_ok = True
                else:
                    logger.warning(f"Render Ken Burns + xfade falhou ({stderr.decode(errors='replace')[:220]}), usando fallback concat...")
        except Exception as motion_err:
            logger.warning(f"Exceção no render Ken Burns ({motion_err}), usando fallback concat...")

    # 2B. Fallback seguro (concat demuxer clássico em 30fps)
    if not rendered_ok:
        concat_file_path = temp_dir / "concat_list.txt"
        with open(concat_file_path, "w", encoding="utf-8") as f:
            for img, dur in zip(image_paths, per_scene_durs):
                f.write(f"file '{os.path.abspath(img)}'\n")
                f.write(f"duration {dur}\n")
            if image_paths:
                f.write(f"file '{os.path.abspath(image_paths[-1])}'\n")

        vf_filters = [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            f"fps={fps}",
            "format=yuv420p",
        ]
        if clean_sub_path:
            vf_filters.append(f"ass='{clean_sub_path}'")

        cmd = [
            ffmpeg,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file_path),
            "-i", os.path.abspath(audio_path),
            "-vf", ",".join(vf_filters),
            "-af", f"apad=whole_dur={target_total_duration}",
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
        _, stderr = await proc.communicate()
        if proc.returncode != 0 and clean_sub_path:
            logger.warning(f"Concat com ASS falhou ({stderr.decode(errors='replace')[:200]}), tentando sem legenda embutida...")
            fallback_vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p"
            cmd[cmd.index("-vf") + 1] = fallback_vf
            proc2 = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr2 = await proc2.communicate()
            if proc2.returncode != 0:
                raise RuntimeError(f"FFmpeg falhou na renderização: {stderr2.decode(errors='replace')[:220]}")
        elif proc.returncode != 0:
            raise RuntimeError(f"FFmpeg falhou na renderização: {stderr.decode(errors='replace')[:220]}")

    # 3. Limpeza de arquivos temporários
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

    # 4. Auditoria final via ffprobe
    probe_data = _probe_media_file(output_video_path)
    streams = probe_data.get("streams") or []
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    probed_duration = float((probe_data.get("format") or {}).get("duration") or target_total_duration)

    file_size_bytes = os.path.getsize(output_video_path) if os.path.exists(output_video_path) else 0
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    logger.info(
        f"Vídeo renderizado com sucesso: {output_video_path} ({file_size_mb} MB, "
        f"duração={probed_duration:.2f}s, video={has_video}, audio={has_audio})"
    )
    return {
        "success": True,
        "video_path": output_video_path,
        "size_mb": file_size_mb,
        "resolution": f"{width}x{height}",
        "aspect_ratio": "9:16",
        "duration_seconds": round(probed_duration, 2),
        "motion_applied": rendered_ok and enable_motion,
        "ffprobe_verified": bool(has_video and has_audio),
    }
