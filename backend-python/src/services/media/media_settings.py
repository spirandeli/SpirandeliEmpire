import os
import shutil
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STORAGE_MEDIA_DIR = BASE_DIR / "storage" / "media"
BIN_DIR = BASE_DIR / "bin"


def _resolve_storage_output_dir() -> Path:
    """
    Resolve o diretório /app/storage/output de forma resiliente tanto no Docker
    quanto no ambiente local do desenvolvedor.
    """
    env_dir = os.getenv("STORAGE_OUTPUT_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Se estiver rodando dentro do container Docker
    docker_path = Path("/app/storage/output")
    if docker_path.exists() or Path("/app").is_dir():
        try:
            docker_path.mkdir(parents=True, exist_ok=True)
            return docker_path
        except (PermissionError, OSError):
            pass

    # Ambiente local
    local_path = BASE_DIR / "storage" / "output"
    local_path.mkdir(parents=True, exist_ok=True)
    return local_path


STORAGE_OUTPUT_DIR = _resolve_storage_output_dir()
STORAGE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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


def _ensure_writable_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(path), 0o777)
        if path.parent.exists():
            os.chmod(str(path.parent), 0o777)
    except OSError:
        pass
    return path


def get_task_media_dir(business_id: int, task_id: int) -> Path:
    """
    Retorna e garante a existência do diretório específico da tarefa.
    """
    path = STORAGE_MEDIA_DIR / f"biz_{business_id}" / f"task_{task_id}"
    return _ensure_writable_dir(path)


def get_task_output_dir(business_id: int, task_id: int) -> Path:
    """
    Retorna e garante a existência do diretório de saída em /app/storage/output.
    """
    path = STORAGE_OUTPUT_DIR / f"biz_{business_id}" / f"task_{task_id}"
    return _ensure_writable_dir(path)


