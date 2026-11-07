import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.dependencies import get_current_user, verify_ai_access
from src.models import AgentConversation, AgentLog, AgentMessage, Business, User
from src.services.gemini_service import reply_to_user

router = APIRouter(prefix="/agent", tags=["Agent"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConversationCreateRequest(BaseModel):
    business_id: Optional[int] = None
    title: Optional[str] = None
    context_type: Optional[str] = "incubator"


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=25000)


def _format_conversation(conv: AgentConversation) -> dict[str, Any]:
    biz_data = None
    if conv.business:
        biz_data = {"id": conv.business.id, "name": conv.business.name, "type": conv.business.type}

    messages_data = []
    if conv.messages:
        for m in conv.messages:
            messages_data.append({
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })

    return {
        "id": conv.id,
        "uuid": conv.uuid,
        "business_id": conv.business_id,
        "business": biz_data,
        "title": conv.title,
        "context_type": conv.context_type,
        "status": conv.status,
        "model": conv.model,
        "messages_count": conv.messages_count,
        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
        "messages": messages_data,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


def _format_message(m: AgentMessage) -> dict[str, Any]:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "tool_name": m.tool_name,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/conversations")
async def index_conversations(
    business_id: Optional[int] = None,
    context_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AgentConversation)
        .options(
            selectinload(AgentConversation.business),
            selectinload(AgentConversation.messages),
        )
        .where(AgentConversation.user_id == current_user.id)
    )
    if business_id:
        query = query.where(AgentConversation.business_id == business_id)
    if context_type:
        query = query.where(AgentConversation.context_type == context_type)
    if status_filter:
        query = query.where(AgentConversation.status == status_filter)

    query = query.order_by(AgentConversation.id.desc())
    res = await db.execute(query)
    convs = res.scalars().all()

    return {"data": [_format_conversation(c) for c in convs]}


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def store_conversation(
    payload: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    business = None
    if payload.business_id:
        biz_res = await db.execute(
            select(Business).where(Business.id == payload.business_id, Business.user_id == current_user.id)
        )
        business = biz_res.scalar_one_or_none()

    ctx = payload.context_type or ("business_chat" if business else "incubator")
    title = payload.title or (f"Operação: {business.name}" if business else "Nova Sessão com COO")

    now = _utc_now()
    conv = AgentConversation(
        uuid=str(uuid.uuid4()),
        user_id=current_user.id,
        business_id=business.id if business else None,
        title=title,
        context_type=ctx,
        status="active",
        model="gemini-3.8",
        messages_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    conv.business = business
    conv.messages = []

    return {"data": _format_conversation(conv)}


@router.get("/conversations/{uuid_str}")
async def show_conversation(
    uuid_str: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(AgentConversation)
        .options(selectinload(AgentConversation.business), selectinload(AgentConversation.messages))
        .where(AgentConversation.uuid == uuid_str, AgentConversation.user_id == current_user.id)
    )
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")

    return {"data": _format_conversation(conv)}


@router.post("/conversations/{uuid_str}/messages")
async def send_message(
    uuid_str: str,
    payload: SendMessageRequest,
    current_user: User = Depends(verify_ai_access),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(AgentConversation)
        .options(selectinload(AgentConversation.business), selectinload(AgentConversation.user))
        .where(AgentConversation.uuid == uuid_str, AgentConversation.user_id == current_user.id)
    )
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")

    conv.user = current_user
    final_reply, new_msgs = await reply_to_user(conv, payload.message, db)

    return {
        "data": _format_message(final_reply),
        "conversation": _format_conversation(conv),
        "new_messages": [_format_message(m) for m in new_msgs],
    }


@router.get("/logs")
async def get_logs(
    after_id: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentLog).where(AgentLog.user_id == current_user.id)
    if after_id is not None:
        query = query.where(AgentLog.id > after_id).order_by(AgentLog.id.asc()).limit(limit)
    else:
        query = query.order_by(AgentLog.id.desc()).limit(limit)

    res = await db.execute(query)
    logs = list(res.scalars().all())
    if after_id is None:
        logs.reverse()

    last_id = max([log.id for log in logs]) if logs else (after_id or 0)

    data = [
        {
            "id": l.id,
            "level": l.level,
            "event": l.event,
            "message": l.message,
            "context": l.context,
            "duration_ms": l.duration_ms,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]

    return {"data": data, "meta": {"last_id": last_id}}
