import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database import get_db
from src.models import (
    ApprovalQueue,
    Business,
    ContentAsset,
    ConversionEvent,
    Task,
    User,
    UserIntegration,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/shortcuts")
async def handle_shortcuts(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_shortcuts_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif x_shortcuts_token:
        token = x_shortcuts_token.strip()

    if not token:
        raise HTTPException(status_code=401, detail="Token do webhook não informado.")

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    res = await db.execute(
        select(UserIntegration).where(
            UserIntegration.provider == "shortcuts",
            UserIntegration.webhook_token_hash == token_hash,
            UserIntegration.status == "connected",
        )
    )
    integ = res.scalar_one_or_none()
    if not integ:
        raise HTTPException(status_code=403, detail="Token do webhook inválido ou revogado.")

    user_res = await db.execute(select(User).where(User.id == integ.user_id))
    user = user_res.scalar_one_or_none()

    integ.last_used_at = _utc_now()
    await db.commit()

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    action = body.get("action", "daily_briefing")

    if action == "capture_task":
        title = body.get("title")
        if not title:
            raise HTTPException(status_code=422, detail="O título da tarefa é obrigatório.")

        biz_res = await db.execute(select(Business).where(Business.user_id == user.id))
        biz = biz_res.scalar_one_or_none()
        if not biz:
            raise HTTPException(status_code=422, detail="Nenhum negócio cadastrado.")

        now = _utc_now()
        task = Task(
            business_id=biz.id,
            user_id=user.id,
            title=title,
            description=body.get("description", "Criada via Atalhos do iPhone / Siri."),
            assignee=body.get("assignee", "user"),
            status="todo_user",
            priority=body.get("priority", "medium"),
            source="shortcuts",
            position=0,
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        return {
            "success": True,
            "message": f"Tarefa #{task.id} criada para {biz.name}.",
            "task": {
                "id": task.id,
                "title": task.title,
                "assignee": task.assignee,
                "status": task.status,
            },
        }

    # Default: daily_briefing
    appr_res = await db.execute(
        select(ApprovalQueue).where(
            ApprovalQueue.user_id == user.id,
            ApprovalQueue.status.in_(["pending", "revision_requested"]),
        )
    )
    pending_items = appr_res.scalars().all()

    tasks_res = await db.execute(
        select(Task).where(
            Task.user_id == user.id,
            Task.status == "todo_user",
            Task.deleted_at.is_(None),
        ).limit(5)
    )
    todo_tasks = tasks_res.scalars().all()

    spoken = (
        f"Olá {user.name}! Você tem {len(pending_items)} entrega(s) aguardando sua revisão "
        f"na Inbox de Supervisão e {len(todo_tasks)} tarefa(s) pendentes para você hoje."
    )

    return {
        "spoken_text": spoken,
        "pending_approvals_count": len(pending_items),
        "pending_approvals": [
            {"id": a.id, "title": a.title, "type": a.type} for a in pending_items
        ],
        "tasks_to_do": [
            {"id": t.id, "title": t.title, "priority": t.priority} for t in todo_tasks
        ],
    }


@router.post("/in/{secret_token}")
async def handle_inbound_webhook(
    secret_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(Business).where(Business.webhook_secret_token == secret_token)
    )
    biz = res.scalar_one_or_none()
    if not biz:
        raise HTTPException(
            status_code=404,
            detail="Webhook secret token inválido ou não cadastrado.",
        )

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    now = _utc_now()
    event_type = body.get("event", body.get("event_type", "purchase_approved"))
    source = body.get("source", "hotmart" if "hottok" in body else "kiwify")
    amount = Decimal(str(body.get("amount", body.get("gross_amount", "197.00"))))

    conv = ConversionEvent(
        business_id=biz.id,
        source_platform=source,
        event_type=event_type,
        external_transaction_id=str(body.get("transaction_id", f"TX-{secrets.token_hex(4)}")),
        gross_amount=amount,
        net_amount=amount * Decimal("0.80"),
        payload_raw=body,
        occurred_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    return {
        "status": "success",
        "message": "Evento processado e registrado com sucesso.",
        "event_id": conv.id,
        "source_platform": conv.source_platform,
        "event_type": conv.event_type,
        "gross_amount": float(conv.gross_amount),
    }
