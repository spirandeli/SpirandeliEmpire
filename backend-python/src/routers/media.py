import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from src.services.media.media_settings import STORAGE_MEDIA_DIR

router = APIRouter(prefix="/media", tags=["Media"])


@router.get("/file/{business_folder}/{task_folder}/{filename}")
async def get_media_file(
    business_folder: str,
    task_folder: str,
    filename: str,
):
    """
    Serve arquivos de mídia gerados (vídeos .mp4, áudios .mp3, imagens .jpg, legendas .srt)
    com suporte para streaming e reprodução no navegador.
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
    media_types = {
        ".mp4": "video/mp4",
        ".mp3": "audio/mpeg",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".srt": "text/plain",
        ".ass": "text/plain",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(target_path),
        media_type=media_type,
        filename=target_path.name,
    )


@router.get("/file/{business_folder}/{task_folder}/scenes/{filename}")
async def get_scene_image(
    business_folder: str,
    task_folder: str,
    filename: str,
):
    """
    Serve imagens individuais de cada cena.
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

    return FileResponse(
        path=str(target_path),
        media_type="image/jpeg",
        filename=target_path.name,
    )

