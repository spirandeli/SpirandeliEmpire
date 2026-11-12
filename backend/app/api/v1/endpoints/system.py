"""SpirandeliEmpire OS 3.1 — System Metrics, Logs & Settings Endpoints"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.database.models import UserModel
from app.services.system_service import system_service

router = APIRouter()


class SettingUpdateRequest(BaseModel):
    value: Dict[str, Any]
    description: str = ""


@router.get("/metrics")
async def get_system_metrics(_user: UserModel = Depends(get_current_user)):
    return system_service.get_vps_metrics()


@router.get("/logs")
async def get_system_logs(
    level: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: UserModel = Depends(get_current_user),
):
    return await system_service.list_logs(level=level, limit=limit, offset=offset)


@router.get("/settings")
async def get_system_settings(_user: UserModel = Depends(get_current_user)):
    return await system_service.get_settings()


@router.put("/settings/{key}")
async def update_system_setting(
    key: str,
    body: SettingUpdateRequest,
    _user: UserModel = Depends(require_role("owner", "admin")),
):
    return await system_service.upsert_setting(key, body.value, body.description)
