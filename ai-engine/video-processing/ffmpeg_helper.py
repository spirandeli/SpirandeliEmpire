"""
SpirandeliEmpire OS - Video Processing Pipeline (FFmpeg)
Builds YouTube Shorts (9:16 vertical 1080x1920) combining:
- Series of images
- Neural voiceover track
- Background soundtrack (mixed at low volume)
- Subtitles (SRT/ASS)
"""
import os
import subprocess
import logging

logger = logging.getLogger("VideoEngine")
FFMPEG_BIN = os.getenv("FFMPEG_BINARY", "ffmpeg")

def render_short_video(
    image_paths: list,
    audio_wav_path: str,
    output_mp4_path: str,
    subtitles_path: str = None,
    fps: int = 30
) -> bool:
    """
    Renders vertical 9:16 video optimized for YouTube Shorts.
    """
    if not os.path.exists(audio_wav_path):
        logger.error(f"Voiceover audio file missing: {audio_wav_path}")
        return False

    os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)

    # Simple 1-image or slideshow vertical render command with FFmpeg
    # Scales and crops to 1080x1920 with high visual quality and AAC audio
    first_image = image_paths[0] if image_paths else None
    if not first_image or not os.path.exists(first_image):
        logger.error("No valid image provided for video render.")
        return False

    # Enforce Video Anti-Ban Pipeline (SKILL.md):
    # 1. C2PA / metadata stripping (-map_metadata -1 -map_chapters -1 -fflags +bitexact)
    # 2. Pixel-level SynthID disruption (rescale 1084x1924 -> crop 1080x1920 + film grain noise=alls=4:allf=t+u + fps 29.97)
    vf_chain = (
        "scale=1084:1924:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "noise=alls=4:allf=t+u,"
        "fps=29.97"
    )
    if subtitles_path and os.path.exists(subtitles_path):
        escaped_sub = subtitles_path.replace("\\", "/").replace(":", "\\:")
        vf_chain += f",subtitles='{escaped_sub}'"

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-loop", "1",
        "-i", first_image,
        "-i", audio_wav_path,
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-fflags", "+bitexact",
        "-flags:v", "+bitexact",
        "-flags:a", "+bitexact",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", vf_chain,
        "-shortest",
        "-movflags", "+faststart",
        output_mp4_path
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        # Optional ExifTool C2PA/JUMBF cleanup if installed
        subprocess.run(["exiftool", "-all=", "-overwrite_original", output_mp4_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Rendered short video with Anti-Ban pipeline successfully: {output_mp4_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode('utf-8', errors='ignore')}")
        return False

