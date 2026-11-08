import os
import shutil
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STORAGE_MEDIA_DIR = BASE_DIR / "storage" / "media"
BIN_DIR = BASE_DIR / "bin"

STORAGE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)


def get_ffmpeg_path() -> str:
    """
    Retorna o executável do FFmpeg, priorizando o binário local empacotado
    em backend-python/bin/ffmpeg ou o que estiver no PATH do sistema.
    """
    local_bin = BIN_DIR / "ffmpeg"
    if local_bin.exists() and os.access(str(local_bin), os.X_OK):
        return str(local_bin)
    system_bin = shutil.which("ffmpeg")
    if system_bin:
        return system_bin
    return str(local_bin)


def get_ffprobe_path() -> str:
    """
    Retorna o executável do FFprobe.
    """
    local_bin = BIN_DIR / "ffprobe"
    if local_bin.exists() and os.access(str(local_bin), os.X_OK):
        return str(local_bin)
    system_bin = shutil.which("ffprobe")
    if system_bin:
        return system_bin
    return str(local_bin)


def get_task_media_dir(business_id: int, task_id: int) -> Path:
    """
    Retorna e garante a existência do diretório específico da tarefa.
    """
    path = STORAGE_MEDIA_DIR / f"biz_{business_id}" / f"task_{task_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path

