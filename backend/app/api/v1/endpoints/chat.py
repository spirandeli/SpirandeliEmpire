"""SpirandeliEmpire OS 3.1 — Chat with Jeffrey (CEO)"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.auth.dependencies import get_current_user, require_role
from app.database.session import AsyncSessionLocal
from app.database.models import ChatMessageModel, UserModel
from app.providers.gemini_provider import gemini_provider
from app.providers.model_resolver import model_router, ModelResolutionError
from app.orchestrator.workflows.manager import workflow_manager
from app.events.manager import event_system

router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    project_id: Optional[str] = None
    trigger_workflow_if_actionable: bool = True


@router.get("/history")
async def get_chat_history(
    project_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
):
    async with AsyncSessionLocal() as session:
        query = select(ChatMessageModel).where(ChatMessageModel.user_id == current_user.id)
        if project_id:
            query = query.where(ChatMessageModel.project_id == project_id)
        res = await session.execute(
            query.order_by(ChatMessageModel.created_at.asc()).offset(offset).limit(limit)
        )
        messages = res.scalars().all()
        return [
            {
                "id": m.id,
                "sender_type": m.sender_type,
                "sender_name": m.sender_name,
                "message": m.message,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ]


@router.post("/message")
async def send_message(
    body: ChatMessageRequest,
    current_user: UserModel = Depends(require_role("ADMIN", "USER")),
):
    user_msg_text = body.message

    async with AsyncSessionLocal() as session:
        user_msg = ChatMessageModel(
            user_id=current_user.id,
            sender_type="user",
            sender_name=current_user.full_name or "Proprietário",
            message=user_msg_text,
            project_id=body.project_id,
        )
        session.add(user_msg)
        await session.commit()

    await event_system.publish(
        event_type="AgentThinking",
        payload={"agent": "Jeffrey", "action": "Analyzing owner request in chat"},
        agent_id="jeffrey",
    )

    is_actionable = any(
        k in user_msg_text.lower()
        for k in [
            "crie", "faça", "desenvolva", "produza", "pesquise",
            "novo projeto", "novo negócio", "inicie", "corte", "shorts", "roteiro"
        ]
    )

    workflow_triggered = None
    if is_actionable and body.trigger_workflow_if_actionable:
        workflow_triggered = await workflow_manager.start_workflow(
            user_request=user_msg_text,
            project_id=body.project_id,
            user_id=current_user.id,
        )

    jeffrey_prompt = (
        f"O proprietário da empresa enviou esta mensagem:\n'{user_msg_text}'\n\n"
        f"Ações automáticas executadas: {'Workflow despachado com sucesso' if workflow_triggered else 'Consulta/Resposta direta'}.\n"
        "Como CEO do SpirandeliEmpire OS, responda ao proprietário com clareza, autoridade, objetividade e reporte quais agentes foram acionados."
    )
    sys_inst = (
        "Você é Jeffrey, CEO e Principal AI Engineer do SpirandeliEmpire OS. "
        "Sempre responda em português com liderança, visão executiva e reporte as ações tomadas com os agentes especialistas."
    )

    try:
        routed = await model_router.generate(
            user_id=current_user.id,
            prompt=jeffrey_prompt,
            system_instruction=sys_inst,
            agent_id="jeffrey",
            project_id=body.project_id,
            temperature=0.3,
        )
        reply_text = routed["content"]
        total_tokens = routed["total_tokens"]
    except ModelResolutionError:
        llm_res = await gemini_provider.generate(
            prompt=jeffrey_prompt,
            system_instruction=sys_inst,
            temperature=0.3,
        )
        reply_text = llm_res.content
        total_tokens = llm_res.total_tokens

    async with AsyncSessionLocal() as session:
        jeffrey_msg = ChatMessageModel(
            user_id=current_user.id,
            sender_type="agent",
            sender_name="Jeffrey (CEO)",
            agent_id="jeffrey",
            message=reply_text,
            project_id=body.project_id,
            metadata_json={"workflow_id": workflow_triggered.get("workflow_id") if workflow_triggered else None},
        )
        session.add(jeffrey_msg)
        await session.commit()

    return {
        "reply": reply_text,
        "workflow": workflow_triggered,
        "token_usage": total_tokens,
    }
