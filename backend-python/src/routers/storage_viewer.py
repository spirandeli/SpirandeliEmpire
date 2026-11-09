"""
Router do Storage Viewer e Gerenciamento de Outputs ABVOS.
Expõe endpoints para varrer recursivamente /app/storage/output/, agrupar arquivos
por business_id e task_id, e disponibilizar URLs seguras de streaming e download.
"""
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.database import get_db, AsyncSessionLocal
from src.dependencies import get_current_user
from src.models import Business, Task, User
from src.services.media.media_settings import (
    STORAGE_OUTPUT_DIR,
    STORAGE_MEDIA_DIR,
    get_task_output_dir,
)
from src.services.media.task_dispatcher import dispatch_series_video_tasks
from src.services.media.pipeline import _persist_video_progress
from src.services.task_executor_service import execute_agent_task

logger = logging.getLogger("abvos.routers.storage_viewer")

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

CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".srt": "text/plain; charset=utf-8",
    ".ass": "text/plain; charset=utf-8",
}


async def _bg_render_series_task(task_id: int, user_id: int):
    """
    Worker assíncrono em background que executa o pipeline completo de vídeo
    (20 cenas + TTS + Legendas + FFmpeg) para uma tarefa e salva em /app/storage/output/.
    """
    try:
        async with AsyncSessionLocal() as session:
            u_res = await session.execute(select(User).where(User.id == user_id))
            user = u_res.scalar_one_or_none()
            if not user:
                return
            await execute_agent_task(session, task_id, user)
    except Exception as exc:
        logger.error(f"Erro ao renderizar tarefa #{task_id} em background: {exc}")


def _file_metadata(f_path: Path, base_dir: Path, mount_prefix: str = "/outputs") -> Dict[str, Any]:
    stat = f_path.stat()
    ext = f_path.suffix.lower()
    rel_path = f_path.relative_to(base_dir).as_posix()
    size_bytes = stat.st_size
    size_mb = round(size_bytes / (1024 * 1024), 2)
    mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    cr_time = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()

    file_type = ALLOWED_EXTENSIONS.get(ext, "other")
    static_url = f"{mount_prefix}/{rel_path}"
    encoded_rel = quote(rel_path, safe="/")

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
        "download_url": f"/api/v1/storage/download?path={encoded_rel}",
    }


def scan_storage_outputs() -> List[Dict[str, Any]]:
    """
    Varre recursivamente o diretório de outputs (/app/storage/output/)
    e complementarmente storage/media, sincronizando arquivos ausentes e
    extraindo metadados sem duplicatas por relative_path.
    """
    results: List[Dict[str, Any]] = []
    scanned_rel_paths = set()

    # Prioriza STORAGE_OUTPUT_DIR (/app/storage/output)
    directories_to_scan = [(STORAGE_OUTPUT_DIR, "/outputs")]
    if STORAGE_MEDIA_DIR.exists() and STORAGE_MEDIA_DIR.resolve() != STORAGE_OUTPUT_DIR.resolve():
        directories_to_scan.append((STORAGE_MEDIA_DIR, "/media"))

    for base_dir, mount_prefix in directories_to_scan:
        if not base_dir.exists():
            continue

        for root, dirs, files in os.walk(base_dir):
            # Ignora diretórios temporários de renderização FFmpeg
            dirs[:] = [d for d in dirs if d != "render_tmp" and not d.startswith(".")]

            for file_name in files:
                if file_name.startswith("."):
                    continue

                full_path = Path(root) / file_name
                ext = full_path.suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue

                try:
                    rel_path = full_path.relative_to(base_dir).as_posix()
                except ValueError:
                    continue

                # Evita duplicatas pelo caminho relativo (ex: biz_1/task_1/video.mp4 em output e media)
                if rel_path in scanned_rel_paths:
                    continue

                # Se o arquivo veio de STORAGE_MEDIA_DIR e ainda não está em STORAGE_OUTPUT_DIR,
                # sincroniza para STORAGE_OUTPUT_DIR para manter tudo unificado em /outputs/
                effective_path = full_path
                effective_base = base_dir
                effective_prefix = mount_prefix
                if base_dir == STORAGE_MEDIA_DIR:
                    target_out = STORAGE_OUTPUT_DIR / rel_path
                    try:
                        target_out.parent.mkdir(parents=True, exist_ok=True)
                        if not target_out.exists():
                            shutil.copy2(str(full_path), str(target_out))
                        effective_path = target_out
                        effective_base = STORAGE_OUTPUT_DIR
                        effective_prefix = "/outputs"
                    except Exception:
                        pass

                scanned_rel_paths.add(rel_path)
                meta = _file_metadata(effective_path, effective_base, effective_prefix)

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


class BatchDeleteFilesRequest(BaseModel):
    paths: List[str]


def _cleanup_empty_parents(file_path: Path, base_root: Path):
    """Remove diretórios pais vazios até atingir base_root."""
    try:
        curr = file_path.parent
        resolved_root = base_root.resolve()
        while curr.exists() and curr.resolve() != resolved_root and str(curr.resolve()).startswith(str(resolved_root)):
            if not any(curr.iterdir()):
                curr.rmdir()
                curr = curr.parent
            else:
                break
    except Exception:
        pass


def _delete_relative_path_everywhere(rel_path: str) -> bool:
    """
    Remove um arquivo relativo tanto de STORAGE_OUTPUT_DIR quanto de STORAGE_MEDIA_DIR
    para impedir que a sincronização recopie arquivos excluídos pelo usuário.
    """
    clean_rel = rel_path.lstrip("/").replace("\\", "/")
    if not clean_rel or ".." in clean_rel.split("/"):
        raise ValueError("Caminho de arquivo inválido.")

    deleted_any = False
    for base_dir in (STORAGE_OUTPUT_DIR, STORAGE_MEDIA_DIR):
        if not base_dir.exists():
            continue
        candidate = (base_dir / clean_rel).resolve()
        if str(candidate).startswith(str(base_dir.resolve())):
            if candidate.is_file():
                candidate.unlink(missing_ok=True)
                _cleanup_empty_parents(candidate, base_dir)
                deleted_any = True
            elif candidate.is_dir():
                shutil.rmtree(candidate, ignore_errors=True)
                _cleanup_empty_parents(candidate, base_dir)
                deleted_any = True

    return deleted_any


def delete_task_storage_dirs(task_id: int, business_id: Optional[int] = None) -> int:
    """
    Remove todos os diretórios e arquivos de mídia/output associados a uma task_id.
    Retorna a quantidade de arquivos removidos.
    """
    removed_files = 0
    for base_dir in (STORAGE_OUTPUT_DIR, STORAGE_MEDIA_DIR):
        if not base_dir.exists():
            continue
        patterns = [f"biz_{business_id}/task_{task_id}"] if business_id else []
        patterns.append(f"*/task_{task_id}")
        seen_dirs = set()
        for pat in patterns:
            for match_dir in base_dir.glob(pat):
                if match_dir.is_dir() and match_dir.resolve() not in seen_dirs:
                    seen_dirs.add(match_dir.resolve())
                    for root, _, files in os.walk(match_dir):
                        removed_files += len(files)
                    shutil.rmtree(match_dir, ignore_errors=True)
                    _cleanup_empty_parents(match_dir, base_dir)
    return removed_files


@router.get("/download")
async def download_storage_file(
    path: str = Query(..., description="Caminho relativo do arquivo dentro de storage/output"),
):
    """
    Endpoint dedicado para download direto (1-clique) com header Content-Disposition: attachment.
    """
    clean_rel = path.lstrip("/").replace("\\", "/")
    if ".." in clean_rel.split("/"):
        raise HTTPException(status_code=400, detail="Caminho de arquivo inválido.")

    candidate_out = (STORAGE_OUTPUT_DIR / clean_rel).resolve()
    if str(candidate_out).startswith(str(STORAGE_OUTPUT_DIR.resolve())) and candidate_out.is_file():
        target = candidate_out
    else:
        candidate_media = (STORAGE_MEDIA_DIR / clean_rel).resolve()
        if str(candidate_media).startswith(str(STORAGE_MEDIA_DIR.resolve())) and candidate_media.is_file():
            target = candidate_media
        else:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado no storage.")

    ext = target.suffix.lower()
    media_type = CONTENT_TYPES.get(ext, "application/octet-stream")
    return FileResponse(
        path=str(target),
        filename=target.name,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{target.name}"'},
    )


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
    e URL de acesso estático, além das tarefas de vídeo do Kanban.
    """
    raw_files = scan_storage_outputs()

    # Carrega metadados de tarefas do banco para enriquecer a resposta e resolver business_id
    file_task_ids = {f["task_id"] for f in raw_files if f["task_id"] > 0}

    tasks_map: Dict[int, Dict[str, Any]] = {}
    if file_task_ids:
        t_res = await db.execute(select(Task).where(Task.id.in_(file_task_ids)))
        for t in t_res.scalars().all():
            tasks_map[t.id] = {
                "id": t.id,
                "business_id": t.business_id,
                "title": t.title,
                "status": t.status,
                "status_log": getattr(t, "status_log", None),
                "description": t.description,
                "payload": t.payload,
                "video_progress": (t.payload or {}).get("video_progress"),
            }

    # Resolve business_id via task quando ausente na pasta
    for f in raw_files:
        t_info = tasks_map.get(f["task_id"])
        if t_info:
            if not f["business_id"] and t_info.get("business_id"):
                f["business_id"] = t_info["business_id"]
            f["task_title"] = t_info["title"]
            f["task_status"] = t_info["status"]
            f["video_progress"] = t_info["video_progress"]

    # Carrega negócios para enriquecer nomes
    biz_ids = {f["business_id"] for f in raw_files if f["business_id"] > 0}
    biz_map: Dict[int, Dict[str, Any]] = {}
    if biz_ids:
        b_res = await db.execute(select(Business).where(Business.id.in_(biz_ids)))
        for b in b_res.scalars().all():
            biz_map[b.id] = {
                "id": b.id,
                "name": b.name,
                "niche": b.niche,
                "archetype": b.archetype,
            }

    for f in raw_files:
        b_info = biz_map.get(f["business_id"])
        f["business_name"] = b_info["name"] if b_info else (f"Venture #{f['business_id']}" if f["business_id"] else "Geral")

    # Aplica filtros se informados
    if business_id is not None:
        raw_files = [f for f in raw_files if f["business_id"] == business_id]
    if task_id is not None:
        raw_files = [f for f in raw_files if f["task_id"] == task_id]
    if file_type:
        raw_files = [f for f in raw_files if f["type"] == file_type]

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
    rendered_task_ids = {v["task_id"] for v in all_videos if v["task_id"] > 0}

    # Busca tarefas de vídeo do usuário no Kanban para exibir fila de renderização
    series_query = select(Task).where(
        Task.user_id == current_user.id,
        Task.deleted_at.is_(None),
        or_(
            Task.agent_action == "render_video_series",
            Task.title.ilike("%[Vídeo]%"),
            Task.title.ilike("%Gerar Vídeo%"),
            Task.title.ilike("%Série%"),
        ),
    )
    if business_id is not None:
        series_query = series_query.where(Task.business_id == business_id)

    s_res = await db.execute(series_query.order_by(Task.id.desc()).limit(20))
    series_tasks = []
    for st in s_res.scalars().all():
        vp = (st.payload or {}).get("video_progress") or {}
        has_vid = st.id in rendered_task_ids
        series_tasks.append({
            "id": st.id,
            "business_id": st.business_id,
            "title": st.title,
            "status": st.status,
            "status_log": getattr(st, "status_log", None) or vp.get("status_text") or (st.description or "").split("\n")[0],
            "percent": 100.0 if has_vid else float(vp.get("percent", 100.0 if st.status == "done" else 0.0)),
            "stage": "done" if has_vid else vp.get("stage", "done" if st.status == "done" else "pending"),
            "has_rendered_video": has_vid,
        })

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
        "series_tasks": series_tasks,
    }


@router.post("/series/dispatch")
async def dispatch_series(
    payload: DispatchSeriesRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara a criação em lote das 3 tarefas da série no Kanban do ABVOS:
    - [Vídeo] Série 01 - Parte 1 (Geração de Assets, TTS e FFmpeg)
    - [Vídeo] Série 01 - Parte 2 (Geração de Assets, TTS e FFmpeg)
    - [Vídeo] Série 01 - Parte 3 (Geração de Assets, TTS e FFmpeg)
    Se auto_execute_part_1=True, dispara o worker em background para renderizar o vídeo.
    """
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
        auto_execute_part_1=bool(payload.auto_execute_part_1),
    )

    if payload.auto_execute_part_1 and tasks:
        # Escolhe a primeira tarefa que ainda não está concluída com vídeo no disco
        target_task = tasks[0]
        for t in tasks:
            out_dir = get_task_output_dir(biz.id, t.id)
            has_mp4 = any(out_dir.glob("*.mp4"))
            if not has_mp4:
                target_task = t
                break

        await _persist_video_progress(
            task_id=target_task.id,
            business_id=biz.id,
            current_scene=0,
            total_scenes=20,
            stage="prompts",
            percent=0.0,
        )
        await db.refresh(target_task)
        background_tasks.add_task(_bg_render_series_task, target_task.id, current_user.id)

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


@router.post("/tasks/{task_id}/render")
async def trigger_task_video_render(
    task_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dispara sob demanda a renderização completa de vídeo (20 cenas + TTS + FFmpeg)
    para uma tarefa específica diretamente pela Galeria de Produção.
    """
    t_res = await db.execute(
        select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
    )
    task = t_res.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    if task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso não autorizado à tarefa.")

    await _persist_video_progress(
        task_id=task.id,
        business_id=task.business_id,
        current_scene=0,
        total_scenes=20,
        stage="prompts",
        percent=0.0,
    )
    background_tasks.add_task(_bg_render_series_task, task.id, current_user.id)

    return {
        "status": "started",
        "task_id": task.id,
        "message": f"Renderização iniciada para '{task.title}'. O progresso será atualizado automaticamente.",
    }


@router.delete("/files")
async def delete_storage_file(
    path: str = Query(..., description="Caminho relativo do arquivo dentro de storage/output"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exclui um arquivo específico (.mp4, .mp3, .jpg, .png, .srt) do storage da VPS
    (tanto em /app/storage/output quanto em /app/storage/media).
    Se for o vídeo principal de uma tarefa, atualiza os metadados da tarefa.
    """
    try:
        deleted = _delete_relative_path_everywhere(path)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    if not deleted:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no storage.")

    # Se excluiu um vídeo .mp4 de uma task, atualiza o status da task se não restarem vídeos
    task_match = re.search(r"task_(\d+)", path)
    if task_match and path.lower().endswith(".mp4"):
        t_id = int(task_match.group(1))
        t_res = await db.execute(select(Task).where(Task.id == t_id))
        task_obj = t_res.scalar_one_or_none()
        if task_obj:
            payload_copy = dict(task_obj.payload or {})
            if "video_progress" in payload_copy:
                payload_copy["video_progress"]["stage"] = "pending"
                payload_copy["video_progress"]["percent"] = 0.0
                payload_copy["video_progress"]["status_log"] = "Vídeo excluído pelo operador. Pronto para re-renderizar."
                task_obj.payload = payload_copy
            if isinstance(task_obj.result, dict):
                res_copy = dict(task_obj.result)
                res_copy.pop("video_url", None)
                if isinstance(res_copy.get("media"), dict):
                    res_copy["media"].pop("video", None)
                task_obj.result = res_copy
            task_obj.status_log = "Vídeo excluído pelo operador."
            await db.commit()

    return {
        "status": "deleted",
        "path": path,
        "message": f"Arquivo '{Path(path).name}' excluído com sucesso da VPS.",
    }


@router.post("/files/delete-batch")
async def delete_storage_files_batch(
    payload: BatchDeleteFilesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exclui múltiplos arquivos selecionados em lote no Storage Viewer.
    """
    deleted_paths = []
    errors = []
    affected_task_ids = set()

    for rel_path in payload.paths:
        try:
            if _delete_relative_path_everywhere(rel_path):
                deleted_paths.append(rel_path)
                tm = re.search(r"task_(\d+)", rel_path)
                if tm and rel_path.lower().endswith(".mp4"):
                    affected_task_ids.add(int(tm.group(1)))
            else:
                errors.append({"path": rel_path, "error": "Não encontrado"})
        except Exception as e:
            errors.append({"path": rel_path, "error": str(e)})

    if affected_task_ids:
        t_res = await db.execute(select(Task).where(Task.id.in_(affected_task_ids)))
        for task_obj in t_res.scalars().all():
            payload_copy = dict(task_obj.payload or {})
            if "video_progress" in payload_copy:
                payload_copy["video_progress"]["stage"] = "pending"
                payload_copy["video_progress"]["percent"] = 0.0
                payload_copy["video_progress"]["status_log"] = "Vídeo excluído em lote."
                task_obj.payload = payload_copy
            task_obj.status_log = "Vídeo excluído pelo operador."
        await db.commit()

    return {
        "status": "deleted",
        "deleted_count": len(deleted_paths),
        "deleted_paths": deleted_paths,
        "errors": errors,
        "message": f"{len(deleted_paths)} arquivo(s) excluído(s) com sucesso da VPS.",
    }


@router.delete("/tasks/{task_id}/files")
async def delete_task_all_files(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exclui todos os arquivos de mídia (.mp4, .mp3, .srt, cenas .jpg/.png) de uma tarefa específica
    e reseta seu estado de vídeo para permitir nova geração limpa.
    """
    t_res = await db.execute(select(Task).where(Task.id == task_id))
    task_obj = t_res.scalar_one_or_none()
    biz_id = task_obj.business_id if task_obj else None

    removed_count = delete_task_storage_dirs(task_id=task_id, business_id=biz_id)

    if task_obj:
        payload_copy = dict(task_obj.payload or {})
        payload_copy["video_progress"] = {
            "stage": "pending",
            "percent": 0.0,
            "current_scene": 0,
            "total_scenes": 20,
            "status_log": "Arquivos limpos pelo operador. Pronto para nova geração.",
            "output_path": "/app/storage/output/",
        }
        task_obj.payload = payload_copy
        task_obj.status_log = "Arquivos limpos pelo operador. Pronto para nova geração."
        if isinstance(task_obj.result, dict):
            res_copy = dict(task_obj.result)
            res_copy.pop("video_url", None)
            res_copy.pop("audio_url", None)
            res_copy.pop("srt_url", None)
            res_copy.pop("media", None)
            task_obj.result = res_copy
        if task_obj.status == "done":
            task_obj.status = "backlog"
            task_obj.completed_at = None
        await db.commit()

    return {
        "status": "cleared",
        "task_id": task_id,
        "removed_files_count": removed_count,
        "message": f"Todos os arquivos da Tarefa #{task_id} foram excluídos da VPS.",
    }


@router.post("/cleanup")
async def cleanup_invalid_and_orphan_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Varre /app/storage/output e /app/storage/media removendo:
    1. Arquivos corrompidos, vazios ou mocks de teste (< 256 bytes);
    2. Pastas de tarefas que já foram excluídas no banco de dados (deleted_at IS NOT NULL);
    3. Diretórios vazios órfãos.
    """
    removed_files = 0
    removed_dirs = 0

    # Identifica tasks deletadas no banco
    del_res = await db.execute(select(Task.id).where(Task.deleted_at.is_not(None)))
    deleted_task_ids = set(del_res.scalars().all())

    for base_dir in (STORAGE_OUTPUT_DIR, STORAGE_MEDIA_DIR):
        if not base_dir.exists():
            continue

        for root, dirs, files in os.walk(base_dir, topdown=False):
            root_path = Path(root)
            if root_path.resolve() == base_dir.resolve():
                continue

            # Verifica se pertence a uma task deletada
            tm = re.search(r"task_(\d+)", root_path.as_posix())
            if tm and int(tm.group(1)) in deleted_task_ids:
                removed_files += len(files)
                shutil.rmtree(root_path, ignore_errors=True)
                removed_dirs += 1
                continue

            for f_name in files:
                if f_name == ".gitkeep":
                    continue
                f_path = root_path / f_name
                try:
                    if f_path.stat().st_size < 256:
                        f_path.unlink(missing_ok=True)
                        removed_files += 1
                except Exception:
                    pass

            try:
                if root_path.exists() and not any(root_path.iterdir()):
                    root_path.rmdir()
                    removed_dirs += 1
            except Exception:
                pass

    return {
        "status": "cleaned",
        "removed_files": removed_files,
        "removed_dirs": removed_dirs,
        "message": f"Limpeza concluída: {removed_files} arquivo(s) inválido(s)/órfão(s) e {removed_dirs} pasta(s) vazia(s) removidos.",
    }
