"""
SpirandeliEmpire OS - TikTok Shop Affiliate Video Renderer
Composição de vídeo vertical 9:16 (1080x1920) para TikTok.
Combina: b-roll de fundo + narração IA + legendas dinâmicas.

Chamado pelo orquestrador n8n via Execute Command:
    python3 render_tiktok_video.py <audio_path> <bg_video_path> <output_path> "<script_text>"
"""

import os
import sys
import logging
import textwrap

logger = logging.getLogger("TikTokRenderer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Configurações de Vídeo ---
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
FPS = 30
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
BITRATE = "5000k"

# --- Configurações de Legenda ---
CAPTION_FONT = "Arial-Bold"
CAPTION_FONTSIZE = 65
CAPTION_COLOR = "yellow"
CAPTION_STROKE_COLOR = "black"
CAPTION_STROKE_WIDTH = 3
CAPTION_MAX_CHARS_PER_LINE = 32


def _split_into_phrases(text: str, max_chars: int = CAPTION_MAX_CHARS_PER_LINE) -> list[str]:
    """
    Quebra o roteiro em frases curtas para exibição como legenda progressiva.
    Preserva pontuação natural e quebra linhas longas.
    """
    # Divide por pontuação natural primeiro
    import re
    sentences = re.split(r'(?<=[.!?,;])\s+', text.strip())
    phrases = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        # Quebra frases longas em linhas de max_chars
        if len(s) > max_chars:
            wrapped = textwrap.wrap(s, width=max_chars)
            phrases.extend(wrapped)
        else:
            phrases.append(s)
    return phrases if phrases else [text]


def create_tiktok_video(
    audio_path: str,
    background_video_path: str,
    output_path: str,
    text_script: str
) -> bool:
    """
    Renderiza um vídeo TikTok vertical 9:16 com b-roll, narração e legendas dinâmicas.

    Args:
        audio_path:              Caminho para o arquivo .mp3 / .wav gerado pelo XTTS.
        background_video_path:   Caminho para o vídeo de fundo (b-roll).
        output_path:             Caminho de saída do vídeo final .mp4.
        text_script:             Roteiro completo para exibição como legenda.

    Returns:
        True se renderizou com sucesso, False caso contrário.
    """
    # Validação de entradas
    for path, label in [(audio_path, "Áudio"), (background_video_path, "B-roll")]:
        if not os.path.exists(path):
            logger.error(f"{label} não encontrado: {path}")
            return False

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Tenta MoviePy primeiro; se não estiver instalado, usa o motor nativo FFmpeg com Anti-Ban Pipeline
    try:
        from moviepy.editor import (
            AudioFileClip, VideoFileClip, TextClip, CompositeVideoClip
        )
    except ImportError:
        logger.info("MoviePy ausente — utilizando renderizador nativo FFmpeg + Anti-Ban Pipeline (C2PA Strip + SynthID Disruption)...")
        return _render_via_ffmpeg_antiban(audio_path, background_video_path, output_path, text_script)

    try:
        # 1. Carrega o áudio gerado pela IA
        logger.info(f"Carregando áudio: {audio_path}")
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # 2. Carrega e redimensiona o b-roll para 9:16 vertical
        logger.info(f"Carregando b-roll: {background_video_path}")
        bg_video = (
            VideoFileClip(background_video_path, audio=False)
            .subclip(0, min(duration, VideoFileClip(background_video_path).duration))
            .resize((TARGET_WIDTH, TARGET_HEIGHT))
            .loop(duration=duration)   # Faz loop se b-roll for mais curto que o áudio
        )

        # 3. Gera legendas dinâmicas progressivas
        phrases = _split_into_phrases(text_script)
        time_per_phrase = duration / max(len(phrases), 1)

        caption_clips = []
        for i, phrase in enumerate(phrases):
            if not phrase.strip():
                continue
            start_time = i * time_per_phrase
            txt = (
                TextClip(
                    phrase,
                    fontsize=CAPTION_FONTSIZE,
                    color=CAPTION_COLOR,
                    font=CAPTION_FONT,
                    stroke_color=CAPTION_STROKE_COLOR,
                    stroke_width=CAPTION_STROKE_WIDTH,
                    method="caption",
                    size=(TARGET_WIDTH - 80, None),   # Margem lateral de 40px cada lado
                    align="center"
                )
                .set_start(start_time)
                .set_duration(time_per_phrase)
                .set_position(("center", TARGET_HEIGHT * 0.65))  # 65% da altura (abaixo do meio)
            )
            caption_clips.append(txt)

        logger.info(f"Legendas geradas: {len(caption_clips)} frases | {time_per_phrase:.1f}s cada")

        # 4. Composição final
        video_final = CompositeVideoClip([bg_video] + caption_clips, size=(TARGET_WIDTH, TARGET_HEIGHT))
        video_final = video_final.set_audio(audio).set_duration(duration)

        # 5. Exportação otimizada para TikTok (H.264 + AAC, 30fps, 5Mbps)
        logger.info(f"Renderizando vídeo final: {output_path}")
        video_final.write_videofile(
            output_path,
            fps=FPS,
            codec=VIDEO_CODEC,
            audio_codec=AUDIO_CODEC,
            bitrate=BITRATE,
            temp_audiofile="/tmp/tiktok_temp_audio.m4a",
            remove_temp=True,
            logger=None   # Silencia barra de progresso do MoviePy no log
        )

        logger.info(f"✅ Vídeo renderizado com sucesso: {output_path}")
        _apply_antiban_postprocess(output_path)
        return True

    except Exception as e:
        logger.warning(f"MoviePy falhou ({e}), acionando fallback nativo FFmpeg Anti-Ban...")
        return _render_via_ffmpeg_antiban(audio_path, background_video_path, output_path, text_script)


def _format_srt_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def _render_via_ffmpeg_antiban(
    audio_path: str,
    background_video_path: str,
    output_path: str,
    text_script: str
) -> bool:
    """
    Renderiza vídeo TikTok 9:16 diretamente via FFmpeg aplicando o Video Anti-Ban Pipeline completo:
      1. Remoção de metadados C2PA / JUMBF / XMP (-map_metadata -1 + exiftool)
      2. Humanização Pixel-Level Anti-SynthID (rescale 1084x1924 -> crop 1080x1920 + film grain noise=alls=4 + fps 29.97)
      3. Legendas dinâmicas geradas em SRT
    """
    import subprocess
    import tempfile

    try:
        # Obter duração do áudio via ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        duration = max(1.0, float(probe_res.stdout.strip() or "30.0"))
    except Exception:
        duration = 30.0

    phrases = _split_into_phrases(text_script)
    time_per_phrase = duration / max(len(phrases), 1)

    srt_file = tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False, encoding="utf-8")
    try:
        for idx, phrase in enumerate(phrases, 1):
            start_t = (idx - 1) * time_per_phrase
            end_t = idx * time_per_phrase
            srt_file.write(f"{idx}\n{_format_srt_time(start_t)} --> {_format_srt_time(end_t)}\n{phrase}\n\n")
        srt_file.close()

        escaped_srt = srt_file.name.replace("\\", "/").replace(":", "\\:")
        vf_filter = (
            "scale=1084:1924:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "noise=alls=4:allf=t+u,"
            "fps=29.97,"
            f"subtitles='{escaped_srt}':force_style='Fontsize=18,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=65'"
        )

        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", background_video_path,
            "-i", audio_path,
            "-map", "0:v:0", "-map", "1:a:0",
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-fflags", "+bitexact",
            "-flags:v", "+bitexact",
            "-flags:a", "+bitexact",
            "-vf", vf_filter,
            "-c:v", VIDEO_CODEC, "-preset", "fast", "-crf", "20", "-b:v", BITRATE,
            "-c:a", AUDIO_CODEC, "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        _apply_antiban_postprocess(output_path)
        logger.info(f"✅ Vídeo TikTok renderizado via FFmpeg Anti-Ban: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Falha no FFmpeg Anti-Ban renderer: {e}")
        return False
    finally:
        if os.path.exists(srt_file.name):
            os.unlink(srt_file.name)


def _apply_antiban_postprocess(video_path: str) -> None:
    """Executa exiftool para garantir remoção total de átomos C2PA/JUMBF/XMP."""
    import subprocess
    try:
        subprocess.run(
            ["exiftool", "-all=", "-overwrite_original", video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )
    except Exception:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Uso: python3 render_tiktok_video.py <audio> <bg_video> <output> \"<roteiro>\"")
        sys.exit(1)

    audio_file = sys.argv[1]
    bg_file    = sys.argv[2]
    out_file   = sys.argv[3]
    script_txt = sys.argv[4]

    success = create_tiktok_video(audio_file, bg_file, out_file, script_txt)
    sys.exit(0 if success else 1)

