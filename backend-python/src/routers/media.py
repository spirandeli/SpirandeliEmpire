import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from src.services.media.media_settings import STORAGE_MEDIA_DIR

router = APIRouter(prefix="/media", tags=["Media"])

MEDIA_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".tts": "audio/mpeg",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".srt": "text/plain; charset=utf-8",
    ".ass": "text/plain; charset=utf-8",
    ".vtt": "text/vtt; charset=utf-8",
    ".json": "application/json",
}


def scan_task_media_dir(task_id: int, business_id: Optional[int] = None) -> dict[str, Any]:
    """
    Escaneia o diretório de saída de mídia de uma tarefa e retorna um manifesto
    estruturado com vídeos, áudios, imagens de cenas e legendas disponíveis,
    incluindo metadados de tamanho, data e URLs diretas de preview e download.
    """
    biz_folder = f"biz_{business_id}" if business_id else None
    task_folder = f"task_{task_id}"

    target_dir: Optional[Path] = None

    if biz_folder:
        candidate = STORAGE_MEDIA_DIR / biz_folder / task_folder
        if candidate.exists() and candidate.is_dir():
            target_dir = candidate

    if not target_dir:
        # Busca em STORAGE_MEDIA_DIR por correspondência da pasta da task
        for p in STORAGE_MEDIA_DIR.glob(f"*/{task_folder}"):
            if p.is_dir():
                target_dir = p
                biz_folder = p.parent.name
                break

    if not target_dir or not target_dir.exists():
        return {
            "task_id": task_id,
            "business_id": business_id,
            "has_media": False,
            "video": None,
            "audio": None,
            "subtitles": [],
            "scenes": [],
            "scenes_count": 0,
            "files": [],
        }

    def file_info(f_path: Path, subfolder: str = "") -> dict[str, Any]:
        stat = f_path.stat()
        ext = f_path.suffix.lower()
        size_bytes = stat.st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)
        created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
        modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

        if ext in (".mp4", ".webm", ".mov", ".mkv"):
            ftype = "video"
        elif ext in (".mp3", ".wav", ".ogg", ".tts", ".m4a", ".aac"):
            ftype = "audio"
        elif ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ftype = "image"
        elif ext in (".srt", ".ass", ".vtt"):
            ftype = "subtitle"
        else:
            ftype = "other"

        if subfolder:
            rel_url = f"/api/media/file/{biz_folder}/{task_folder}/{subfolder}/{f_path.name}"
            down_url = f"/api/media/download/{biz_folder}/{task_folder}/{subfolder}/{f_path.name}"
        else:
            rel_url = f"/api/media/file/{biz_folder}/{task_folder}/{f_path.name}"
            down_url = f"/api/media/download/{biz_folder}/{task_folder}/{f_path.name}"

        return {
            "name": f_path.name,
            "type": ftype,
            "extension": ext,
            "size_bytes": size_bytes,
            "size_mb": size_mb,
            "created_at": created_at,
            "modified_at": modified_at,
            "relative_path": str(f_path.relative_to(STORAGE_MEDIA_DIR)),
            "url": rel_url,
            "download_url": down_url,
        }

    all_files = []
    video_files = []
    audio_files = []
    subtitle_files = []
    scenes = []

    # 1. Arquivos na raiz da tarefa
    for item in sorted(target_dir.iterdir()):
        if item.is_file() and not item.name.startswith("."):
            info = file_info(item)
            all_files.append(info)
            if info["type"] == "video":
                video_files.append(info)
            elif info["type"] == "audio":
                audio_files.append(info)
            elif info["type"] == "subtitle":
                subtitle_files.append(info)

    # 2. Imagens na subpasta scenes/
    scenes_dir = target_dir / "scenes"
    if scenes_dir.exists() and scenes_dir.is_dir():
        for item in sorted(scenes_dir.iterdir()):
            if item.is_file() and not item.name.startswith("."):
                info = file_info(item, subfolder="scenes")
                all_files.append(info)
                if info["type"] == "image":
                    match = re.search(r"scene_?(\d+)", item.name, re.IGNORECASE)
                    scene_num = int(match.group(1)) if match else len(scenes) + 1
                    info["scene_number"] = scene_num
                    scenes.append(info)

    scenes.sort(key=lambda s: s.get("scene_number", 0))

    primary_video = video_files[0] if video_files else None
    primary_audio = audio_files[0] if audio_files else None

    has_media = bool(primary_video or primary_audio or scenes)

    return {
        "task_id": task_id,
        "business_id": business_id,
        "has_media": has_media,
        "video": primary_video,
        "audio": primary_audio,
        "subtitles": subtitle_files,
        "scenes": scenes,
        "scenes_count": len(scenes),
        "files": all_files,
    }


@router.get("/file/{business_folder}/{task_folder}/{filename}")
async def get_media_file(
    business_folder: str,
    task_folder: str,
    filename: str,
    download: bool = Query(False),
):
    """
    Serve arquivos de mídia gerados (vídeos .mp4, áudios .mp3, imagens .jpg, legendas .srt)
    com suporte a streaming (Range requests) e download direto.
    """
    target_path = (STORAGE_MEDIA_DIR / business_folder / task_folder / filename).resolve()

    # Prevenção contra Directory Traversal
    try:
        target_path.relative_to(STORAGE_MEDIA_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado ao diretório de mídia.",
        )

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo de mídia não encontrado.",
        )

    ext = target_path.suffix.lower()
    media_type = MEDIA_CONTENT_TYPES.get(ext, "application/octet-stream")
    disp = "attachment" if download else "inline"

    return FileResponse(
        path=str(target_path),
        media_type=media_type,
        filename=target_path.name,
        content_disposition_type=disp,
    )


@router.get("/download/{business_folder}/{task_folder}/{filename}")
async def download_media_file(
    business_folder: str,
    task_folder: str,
    filename: str,
):
    """
    Endpoint dedicado para download direto do arquivo com Content-Disposition attachment.
    """
    return await get_media_file(
        business_folder=business_folder,
        task_folder=task_folder,
        filename=filename,
        download=True,
    )


@router.get("/file/{business_folder}/{task_folder}/scenes/{filename}")
async def get_scene_image(
    business_folder: str,
    task_folder: str,
    filename: str,
    download: bool = Query(False),
):
    """
    Serve imagens individuais de cada cena gerada.
    """
    target_path = (STORAGE_MEDIA_DIR / business_folder / task_folder / "scenes" / filename).resolve()

    try:
        target_path.relative_to(STORAGE_MEDIA_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado.",
        )

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem de cena não encontrada.",
        )

    ext = target_path.suffix.lower()
    media_type = MEDIA_CONTENT_TYPES.get(ext, "image/jpeg")
    disp = "attachment" if download else "inline"

    return FileResponse(
        path=str(target_path),
        media_type=media_type,
        filename=target_path.name,
        content_disposition_type=disp,
    )


@router.get("/download/{business_folder}/{task_folder}/scenes/{filename}")
async def download_scene_image(
    business_folder: str,
    task_folder: str,
    filename: str,
):
    """
    Endpoint dedicado para download direto de imagem de cena.
    """
    return await get_scene_image(
        business_folder=business_folder,
        task_folder=task_folder,
        filename=filename,
        download=True,
    )


@router.get("/tasks/{task_id}")
async def get_media_by_task(
    task_id: int,
    business_id: Optional[int] = Query(None),
):
    """
    Retorna o manifesto de mídia para uma tarefa específica.
    """
    manifest = scan_task_media_dir(task_id=task_id, business_id=business_id)
    return {"data": manifest}
