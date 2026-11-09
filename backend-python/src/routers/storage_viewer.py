"""
Router do Storage Viewer e Gerenciamento de Outputs ABVOS.
Expõe endpoints para varrer recursivamente /app/storage/output/, agrupar arquivos
por business_id e task_id, e disponibilizar URLs seguras de streaming e download.
"""
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user
from src.models import Business, Task, User
from src.services.media.media_settings import (
    STORAGE_OUTPUT_DIR,
    STORAGE_MEDIA_DIR,
    get_task_output_dir,
)
from src.services.media.task_dispatcher import dispatch_series_video_tasks

router = APIRouter(prefix="/storage", tags=["Storage Viewer"])

ALLOWED_EXTENSIONS = {
    ".mp4": "video",
    ".webm": "video",
    ".mov": "video",
    ".mkv": "video",
    ".mp3": "audio",
    ".wav": "audio",
    ".ogg": "audio",
    ".m4a": "audio",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".srt": "subtitle",
    ".ass": "subtitle",
}


def _file_metadata(f_path: Path, base_dir: Path) -> Dict[str, Any]:
    stat = f_path.stat()
    ext = f_path.suffix.lower()
    rel_path = f_path.relative_to(base_dir).as_posix()
    size_bytes = stat.st_size
    size_mb = round(size_bytes / (1024 * 1024), 2)
    mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    cr_time = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()

    file_type = ALLOWED_EXTENSIONS.get(ext, "other")
    static_url = f"/outputs/{rel_path}"

    return {
        "name": f_path.name,
        "extension": ext,
        "type": file_type,
        "relative_path": rel_path,
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "created_at": cr_time,
        "modified_at": mod_time,
        "static_url": static_url,
        "download_url": f"{static_url}?download=1",
    }


def scan_storage_outputs() -> List[Dict[str, Any]]:
    """
    Varre recursivamente o diretório de outputs (/app/storage/output/)
    e opcionalmente storage/media, extraindo metadados de arquivos .mp4, .mp3 e .png.
    """
    results: List[Dict[str, Any]] = []
    scanned_hashes = set()

    # Prioriza STORAGE_OUTPUT_DIR (/app/storage/output)
    directories_to_scan = [STORAGE_OUTPUT_DIR]
    if STORAGE_MEDIA_DIR.exists() and STORAGE_MEDIA_DIR != STORAGE_OUTPUT_DIR:
        directories_to_scan.append(STORAGE_MEDIA_DIR)

    for base_dir in directories_to_scan:
        if not base_dir.exists():
            continue

        for root, _, files in os.walk(base_dir):
            for file_name in files:
                if file_name.startswith("."):
                    continue

                full_path = Path(root) / file_name
                ext = full_path.suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue

                # Evita duplicatas se um arquivo estiver em múltiplos diretórios escaneados
                unique_key = str(full_path.resolve())
                if unique_key in scanned_hashes:
                    continue
                scanned_hashes.add(unique_key)

                meta = _file_metadata(full_path, base_dir)

                # Extrai business_id e task_id da estrutura de pastas ou nome
                biz_id = 0
                task_id = 0

                biz_match = re.search(r"biz_(\d+)", meta["relative_path"])
                if biz_match:
                    biz_id = int(biz_match.group(1))

                task_match = re.search(r"task_(\d+)", meta["relative_path"])
                if task_match:
                    task_id = int(task_match.group(1))
                else:
                    file_task_match = re.search(r"_task_(\d+)", file_name)
                    if file_task_match:
                        task_id = int(file_task_match.group(1))

                meta["business_id"] = biz_id
                meta["task_id"] = task_id
                results.append(meta)

    # Ordena pelos mais recentes
    results.sort(key=lambda x: x["modified_at"], reverse=True)
    return results


class DispatchSeriesRequest(BaseModel):
    business_id: int
    series_title: Optional[str] = "Série 01 - A Queda de Lúcifer"
    parts_count: Optional[int] = 3
    auto_execute_part_1: Optional[bool] = False


@router.get("/outputs")
async def get_storage_outputs(
    business_id: Optional[int] = None,
    task_id: Optional[int] = None,
    file_type: Optional[str] = Query(None, alias="type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint principal: GET /api/v1/storage/outputs
    Varre o diretório /app/storage/output/ recursivamente.
    Retorna um JSON contendo a lista de arquivos .mp4, .mp3 e .png,
    agrupados por business_id e task_id, informando tamanho, data de modificação
    e URL de acesso estático.
    """
    raw_files = scan_storage_outputs()

    # Aplica filtros se informados
    if business_id is not None:
        raw_files = [f for f in raw_files if f["business_id"] == business_id]
    if task_id is not None:
        raw_files = [f for f in raw_files if f["task_id"] == task_id]
    if file_type:
        raw_files = [f for f in raw_files if f["type"] == file_type]

    # Carrega metadados do banco para enriquecer a resposta
    task_ids = {f["task_id"] for f in raw_files if f["task_id"] > 0}
    biz_ids = {f["business_id"] for f in raw_files if f["business_id"] > 0}

    tasks_map = {}
    if task_ids:
        t_res = await db.execute(select(Task).where(Task.id.in_(task_ids)))
        for t in t_res.scalars().all():
            tasks_map[t.id] = {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "description": t.description,
                "payload": t.payload,
                "video_progress": (t.payload or {}).get("video_progress"),
            }

    biz_map = {}
    if biz_ids:
        b_res = await db.execute(select(Business).where(Business.id.in_(biz_ids)))
        for b in b_res.scalars().all():
            biz_map[b.id] = {
                "id": b.id,
                "name": b.name,
                "niche": b.niche,
                "archetype": b.archetype,
            }

    # Agrupamento por business_id e task_id
    grouped_biz: Dict[int, Dict[str, Any]] = {}

    for f in raw_files:
        b_id = f["business_id"]
        t_id = f["task_id"]

        if b_id not in grouped_biz:
            biz_info = biz_map.get(b_id, {"id": b_id, "name": f"Venture #{b_id}" if b_id else "Geral"})
            grouped_biz[b_id] = {
                "business_id": b_id,
                "business_name": biz_info["name"],
                "tasks": {},
                "total_size_mb": 0.0,
                "total_files": 0,
            }

        biz_group = grouped_biz[b_id]
        biz_group["total_files"] += 1
        biz_group["total_size_mb"] = round(biz_group["total_size_mb"] + f["size_mb"], 2)

        if t_id not in biz_group["tasks"]:
            task_info = tasks_map.get(t_id, {
                "id": t_id,
                "title": f"Tarefa #{t_id}" if t_id else "Arquivos Avulsos",
                "status": "done" if f["type"] == "video" else "in_progress",
                "video_progress": None,
            })
            biz_group["tasks"][t_id] = {
                "task_id": t_id,
                "task_title": task_info["title"],
                "status": task_info.get("status"),
                "video_progress": task_info.get("video_progress"),
                "videos": [],
                "audios": [],
                "images": [],
                "subtitles": [],
                "files": [],
                "total_size_mb": 0.0,
            }

        t_group = biz_group["tasks"][t_id]
        t_group["files"].append(f)
        t_group["total_size_mb"] = round(t_group["total_size_mb"] + f["size_mb"], 2)

        if f["type"] == "video":
            t_group["videos"].append(f)
        elif f["type"] == "audio":
            t_group["audios"].append(f)
        elif f["type"] == "image":
            t_group["images"].append(f)
        elif f["type"] == "subtitle":
            t_group["subtitles"].append(f)

    # Converte dicionários para listas estruturadas
    formatted_groups = []
    for b_id, b_data in grouped_biz.items():
        task_list = []
        for t_id, t_data in b_data["tasks"].items():
            primary_video = t_data["videos"][0] if t_data["videos"] else None
            primary_audio = t_data["audios"][0] if t_data["audios"] else None
            task_list.append({
                "task_id": t_id,
                "task_title": t_data["task_title"],
                "status": t_data["status"],
                "video_progress": t_data["video_progress"],
                "primary_video": primary_video,
                "primary_audio": primary_audio,
                "video_count": len(t_data["videos"]),
                "audio_count": len(t_data["audios"]),
                "image_count": len(t_data["images"]),
                "total_files": len(t_data["files"]),
                "total_size_mb": t_data["total_size_mb"],
                "videos": t_data["videos"],
                "audios": t_data["audios"],
                "images": t_data["images"],
                "files": t_data["files"],
            })
        task_list.sort(key=lambda t: t["task_id"], reverse=True)
        formatted_groups.append({
            "business_id": b_id,
            "business_name": b_data["business_name"],
            "total_files": b_data["total_files"],
            "total_size_mb": b_data["total_size_mb"],
            "tasks": task_list,
        })

    # Extrai todos os vídeos encontrados para facilitar consumo pelo player
    all_videos = [f for f in raw_files if f["type"] == "video"]
    for v in all_videos:
        t_info = tasks_map.get(v["task_id"])
        if t_info:
            v["task_title"] = t_info["title"]
            v["task_status"] = t_info["status"]
            v["video_progress"] = t_info["video_progress"]

    total_size = round(sum(f["size_mb"] for f in raw_files), 2)

    return {
        "status": "success",
        "storage_directory": str(STORAGE_OUTPUT_DIR),
        "total_files": len(raw_files),
        "total_size_mb": total_size,
        "videos_count": len(all_videos),
        "groups": formatted_groups,
        "videos": all_videos,
        "files": raw_files,
    }


@router.post("/series/dispatch")
async def dispatch_series(
    payload: DispatchSeriesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara a criação em lote das 3 tarefas da série no Kanban do ABVOS:
    - [Vídeo] Série 01 - Parte 1 (Geração de Assets, TTS e FFmpeg)
    - [Vídeo] Série 01 - Parte 2 (Geração de Assets, TTS e FFmpeg)
    - [Vídeo] Série 01 - Parte 3 (Geração de Assets, TTS e FFmpeg)
    """
    # Valida se o negócio pertence ao usuário ou se é admin
    biz_stmt = select(Business).where(Business.id == payload.business_id)
    b_res = await db.execute(biz_stmt)
    biz = b_res.scalar_one_or_none()
    if not biz:
        raise HTTPException(status_code=404, detail="Negócio não encontrado.")
    if biz.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso não autorizado ao negócio.")

    tasks = await dispatch_series_video_tasks(
        db=db,
        user_id=current_user.id,
        business_id=biz.id,
        series_title=payload.series_title or "Série 01 - A Queda de Lúcifer",
        parts_count=payload.parts_count or 3,
        auto_execute_part_1=payload.auto_execute_part_1 or False,
    )

    return {
        "message": f"Série '{payload.series_title}' despachada com sucesso no Kanban!",
        "tasks_created": len(tasks),
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "assignee": t.assignee,
                "description": t.description,
            }
            for t in tasks
        ],
    }
