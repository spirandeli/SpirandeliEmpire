"""SpirandeliEmpire OS 3.1 — Integration Hub Endpoints"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth.dependencies import get_current_user, require_role
from app.database.models import UserModel
from app.services.integration_service import integration_service

router = APIRouter()


class SaveCredentialsRequest(BaseModel):
    credentials: str
    config: Optional[Dict[str, Any]] = None


@router.get("/")
async def list_integrations(_user: UserModel = Depends(get_current_user)):
    return await integration_service.list_integrations()


@router.post("/{integration_id}/credentials")
async def save_credentials(
    integration_id: str,
    body: SaveCredentialsRequest,
    _user: UserModel = Depends(require_role("owner", "admin")),
):
    return await integration_service.save_credentials(
        integration_id=integration_id,
        credentials_plain=body.credentials,
        config=body.config,
    )


@router.post("/{integration_id}/test")
async def test_connection(
    integration_id: str,
    _user: UserModel = Depends(require_role("owner", "admin")),
):
    return await integration_service.test_connection(integration_id)
