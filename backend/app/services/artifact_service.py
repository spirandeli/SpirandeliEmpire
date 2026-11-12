"""SpirandeliEmpire OS 3.1 — Artifact Manager Service"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import ArtifactModel
from app.core.config import settings
from app.events.manager import event_system


class ArtifactService:
    async def list_artifacts(
        self, project_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            query = select(ArtifactModel)
            if user_id:
                query = query.where(ArtifactModel.user_id == user_id)
            if project_id:
                query = query.where(ArtifactModel.project_id == project_id)
            result = await session.execute(query.order_by(ArtifactModel.created_at.desc()))
            artifacts = result.scalars().all()
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "artifact_type": a.artifact_type,
                    "file_path": a.file_path,
                    "file_size": a.file_size,
                    "creator_agent": a.creator_agent_id,
                    "project_id": a.project_id,
                    "workflow_id": a.workflow_id,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in artifacts
            ]

    async def get_artifact(
        self, artifact_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            art = await session.get(ArtifactModel, artifact_id)
            if not art or (user_id and art.user_id != user_id):
                return None
            
            content_preview = ""
            p = Path(art.file_path)
            if p.exists() and p.is_file():
                # Read text preview if text-based
                if art.artifact_type in ["code", "document", "script", "subtitle", "logs", "report"]:
                    try:
                        with open(p, "r", encoding="utf-8", errors="replace") as f:
                            content_preview = f.read(10000)
                    except Exception:
                        content_preview = "[Arquivo binário ou ilegível como texto]"

            return {
                "id": art.id,
                "name": art.name,
                "artifact_type": art.artifact_type,
                "file_path": art.file_path,
                "file_size": art.file_size,
                "creator_agent": art.creator_agent_id,
                "project_id": art.project_id,
                "workflow_id": art.workflow_id,
                "preview": content_preview,
                "created_at": art.created_at.isoformat() if art.created_at else None
            }


artifact_service = ArtifactService()

