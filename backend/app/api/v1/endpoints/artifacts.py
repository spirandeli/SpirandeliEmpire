"""SpirandeliEmpire OS 3.1 — Artifacts API Endpoints"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.database.models import UserModel
from app.services.artifact_service import artifact_service

router = APIRouter()


@router.get("/")
async def list_artifacts(
    project_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
):
    items = await artifact_service.list_artifacts(project_id=project_id, user_id=current_user.id)
    return items[offset : offset + limit]


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str, current_user: UserModel = Depends(get_current_user)):
    art = await artifact_service.get_artifact(artifact_id, user_id=current_user.id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return art


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: str, current_user: UserModel = Depends(get_current_user)):
    art = await artifact_service.get_artifact(artifact_id, user_id=current_user.id)
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    target_path = Path(art["file_path"]).resolve()
    storage_root = settings.STORAGE_DIR.resolve()
    if not target_path.is_relative_to(storage_root):
        raise HTTPException(status_code=403, detail="Acesso negado fora do diretório de storage")
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="File on disk not found")

    return FileResponse(
        path=str(target_path),
        filename=os.path.basename(str(target_path)),
        media_type="application/octet-stream",
    )
