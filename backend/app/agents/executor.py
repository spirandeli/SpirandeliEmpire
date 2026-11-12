"""SpirandeliEmpire OS 3.2 — Unified Agent Execution Engine with Model Router"""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.agents.registry import get_agent_by_id
from app.database.session import AsyncSessionLocal
from app.database.models import AgentModel, TaskModel
from app.events.manager import event_system
from app.memory.service import memory_service
from app.providers.gemini_provider import gemini_provider
from app.providers.model_resolver import model_router, ModelResolutionError
from app.tools.registry import tool_registry


class AgentExecutionResult(BaseModel):
    agent_id: str
    task_id: str
    status: str  # completed, failed
    summary: str = ""
    provider: str = ""
    model: str = ""
    tokens_used: int = 0
    artifacts_created: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class AgentExecutor:
    async def execute_task(
        self,
        agent_id: str,
        task_title: str,
        task_description: str,
        workflow_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        task_profile: Optional[str] = None,
        explicit_model_override: Optional[Dict[str, Any]] = None,
        dependency_outputs: Optional[Dict[str, str]] = None,
        tool_call: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> AgentExecutionResult:
        """
        Execute a single agent task with:
        - Dynamic ModelRouter (Gemini / OpenAI / Anthropic) per user/agent/task
        - Multi-user TaskModel & MemoryModel isolation
        - Authorized tool execution & structured output
        """
        defn = get_agent_by_id(agent_id)
        db_task_id = task_id or str(uuid.uuid4())

        async with AsyncSessionLocal() as session:
            existing_task = await session.get(TaskModel, db_task_id)
            if existing_task:
                existing_task.status = "in_progress"
                existing_task.attempts += 1
            else:
                session.add(
                    TaskModel(
                        id=db_task_id,
                        user_id=user_id,
                        project_id=project_id,
                        workflow_id=workflow_id,
                        title=task_title[:256],
                        description=task_description,
                        assigned_agent_id=agent_id,
                        status="in_progress",
                        attempts=1,
                    )
                )

            agent_db = await session.get(AgentModel, agent_id)
            if agent_db:
                agent_db.operational_state = "working"
            await session.commit()

        await event_system.publish(
            event_type="AgentStarted",
            payload={"agent_id": agent_id, "agent": defn.name, "task": task_title, "task_id": db_task_id},
            agent_id=agent_id,
            workflow_id=workflow_id,
            project_id=project_id,
        )

        try:
            memories = await memory_service.list_memories(
                agent_id=agent_id, project_id=project_id, user_id=user_id, limit=5
            )
            memory_ctx = "\n".join(f"- {m['key']}: {m['content'][:300]}" for m in memories)

            dep_ctx = ""
            if dependency_outputs:
                dep_lines = [f"- [{k}]: {v[:500]}" for k, v in dependency_outputs.items()]
                dep_ctx = "\nResultados de etapas anteriores:\n" + "\n".join(dep_lines)

            prompt = (
                f"Tarefa atribuída: {task_title}\n"
                f"Descrição: {task_description[:1500]}\n"
                f"{dep_ctx}\n"
                + (f"\nMemória relevante:\n{memory_ctx}\n" if memory_ctx else "")
                + "\nEntregue uma resposta técnica objetiva, estruturada e verificável."
            )

            temperature = float(defn.generation_config.get("temperature", 0.4))

            # Use dynamic ModelRouter when user_id is present (unless test handler is injected)
            if user_id and gemini_provider._test_handler is None:
                routed = await model_router.generate(
                    user_id=user_id,
                    prompt=prompt,
                    system_instruction=defn.system_prompt,
                    agent_id=agent_id,
                    task_profile=task_profile,
                    project_id=project_id,
                    workflow_id=workflow_id,
                    task_id=db_task_id,
                    explicit_override=explicit_model_override,
                    temperature=temperature,
                )
                content_text = routed["content"]
                used_provider = routed["provider"]
                used_model = routed["model_id"]
                total_tokens = routed["total_tokens"]
            else:
                llm_res = await gemini_provider.generate(
                    prompt=prompt,
                    system_instruction=defn.system_prompt,
                    model=defn.model if defn.model != "dynamic" else None,
                    temperature=temperature,
                )
                content_text = llm_res.content
                used_provider = llm_res.provider
                used_model = llm_res.model
                total_tokens = llm_res.total_tokens

            artifacts_created: List[Dict[str, Any]] = []
            if tool_call:
                t_id = tool_call["tool_id"]
                t_params = dict(tool_call.get("params", {}))
                if t_id in ("file_writer", "script_generator") and not t_params.get("content"):
                    t_params["content"] = content_text
                tool_res = await tool_registry.execute(t_id, t_params, agent_id)
                if not tool_res.success:
                    raise RuntimeError(tool_res.error or f"Tool '{t_id}' failed")
                for path in tool_res.artifacts_created:
                    artifacts_created.append(
                        {
                            "name": tool_call.get("artifact_name", f"Entrega {defn.name}"),
                            "type": tool_call.get("artifact_type", "document"),
                            "path": path,
                            "creator": agent_id,
                        }
                    )

            async with AsyncSessionLocal() as session:
                t_db = await session.get(TaskModel, db_task_id)
                if t_db:
                    t_db.status = "completed"
                    t_db.result_summary = content_text[:2000]
                    t_db.artifacts = [a["path"] for a in artifacts_created]

                a_db = await session.get(AgentModel, agent_id)
                if a_db:
                    a_db.operational_state = "idle"
                    metrics = dict(a_db.metrics or {})
                    metrics["tasks_completed"] = int(metrics.get("tasks_completed", 0)) + 1
                    metrics["token_usage"] = int(metrics.get("token_usage", 0)) + total_tokens
                    a_db.metrics = metrics
                    hist = list(a_db.history or [])
                    hist.append({"task_id": db_task_id, "title": task_title, "status": "completed"})
                    a_db.history = hist[-20:]
                await session.commit()

            await event_system.publish(
                event_type="AgentCompleted",
                payload={"agent_id": agent_id, "task_id": db_task_id, "tokens": total_tokens, "provider": used_provider, "model": used_model},
                agent_id=agent_id,
                workflow_id=workflow_id,
                project_id=project_id,
            )

            return AgentExecutionResult(
                agent_id=agent_id,
                task_id=db_task_id,
                status="completed",
                summary=content_text,
                provider=used_provider,
                model=used_model,
                tokens_used=total_tokens,
                artifacts_created=artifacts_created,
            )

        except Exception as exc:
            err_msg = str(exc).strip() or exc.__class__.__name__
            async with AsyncSessionLocal() as session:
                t_db = await session.get(TaskModel, db_task_id)
                if t_db:
                    t_db.status = "failed"
                    t_db.result_summary = f"Erro: {err_msg}"
                a_db = await session.get(AgentModel, agent_id)
                if a_db:
                    a_db.operational_state = "error"
                await session.commit()

            await event_system.publish(
                event_type="AgentFailed",
                payload={"agent_id": agent_id, "task_id": db_task_id, "error": err_msg},
                agent_id=agent_id,
                workflow_id=workflow_id,
                project_id=project_id,
            )

            return AgentExecutionResult(
                agent_id=agent_id,
                task_id=db_task_id,
                status="failed",
                error=err_msg,
            )


agent_executor = AgentExecutor()
