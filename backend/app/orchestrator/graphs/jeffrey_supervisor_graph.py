"""SpirandeliEmpire OS 3.1 — Jeffrey Supervisor LangGraph Workflow"""

import asyncio
import uuid
from typing import Dict, Any, List, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from app.orchestrator.state.empire_state import EmpireState
from app.orchestrator.checkpoints.checkpoint_manager import checkpoint_manager
from app.orchestrator.checkpoints.persistent_saver import persistent_checkpointer
from app.events.manager import event_system
from app.tools.registry import tool_registry
from app.providers.gemini_provider import gemini_provider
from app.agents.executor import agent_executor

MAX_REPLAN_ITERATIONS = 3
MAX_PARALLEL_AGENTS = 3

BACKUP_AGENT_MAP: Dict[str, str] = {
    "fonseca": "jeffrey",
    "balsini": "noe",
    "noe": "jeffrey",
    "ford": "balsini",
    "jarvis": "balsini",
    "murphy": "jeffrey",
    "script_agent": "jeffrey",
    "news_agent": "jeffrey",
    "voice_agent": "jeffrey",
    "subtitle_agent": "jeffrey",
    "clipador_agent": "video_agent",
    "designer_agent": "jeffrey",
    "video_agent": "clipador_agent",
}


async def interpret_request_node(state: EmpireState) -> Dict[str, Any]:
    workflow_id = state["workflow_id"]
    req = state["user_request"]
    user_id = (state.get("execution_context") or {}).get("user_id")

    await event_system.publish(
        event_type="AgentStarted",
        payload={"agent": "Jeffrey", "action": "Interpreting request", "request": req},
        agent_id="jeffrey",
        workflow_id=workflow_id,
        project_id=state.get("project_id"),
    )

    prompt = (
        f"Como CEO do SpirandeliEmpire, interprete esta solicitação do proprietário "
        f"e defina o objetivo estratégico em uma frase objetiva:\n{req}"
    )

    objective = ""
    if user_id:
        try:
            from app.providers.model_resolver import model_router
            routed = await model_router.generate(
                user_id=user_id,
                prompt=prompt,
                system_instruction="Você é Jeffrey, CEO. Resuma o objetivo em uma frase clara e de alto impacto.",
                agent_id="jeffrey",
                temperature=0.3,
            )
            objective = routed.get("content", "").strip()
        except Exception:
            objective = ""

    if not objective:
        response = await gemini_provider.generate(
            prompt=prompt,
            system_instruction="Você é Jeffrey, CEO. Resuma o objetivo em uma frase clara e de alto impacto.",
            temperature=0.3,
        )
        objective = response.content.strip()

    checkpoint_manager.save_checkpoint(workflow_id, "interpret_request", state, 1)

    return {
        "objective": objective,
        "current_node": "interpret_request",
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def classify_objective_node(state: EmpireState) -> Dict[str, Any]:
    obj = (state.get("objective") or "").lower()
    req = state["user_request"].lower()

    # Prioritize actual user request first
    if any(k in req for k in ["corte", "clip", "clipe", "clipagem"]):
        domain = "clip"
    elif any(k in req for k in ["roteiro", "shorts", "vídeo", "video", "tiktok", "conteúdo", "história", "youtube"]):
        domain = "content"
    elif any(k in req for k in ["desenvolv", "código", "software", "api", "sistema", "app", "site", "migration", "docker"]):
        domain = "development"
    elif any(k in req for k in ["negócio", "startup", "monetiz", "business", "empresa"]):
        domain = "business"
    # Fallback to objective string
    elif any(k in obj for k in ["corte", "clip", "clipe"]):
        domain = "clip"
    elif any(k in obj for k in ["roteiro", "shorts", "vídeo", "video", "conteúdo"]):
        domain = "content"
    elif any(k in obj for k in ["desenvolv", "código", "software", "api"]):
        domain = "development"
    elif any(k in obj for k in ["negócio", "startup", "monetiz"]):
        domain = "business"
    else:
        domain = "supervisor"

    return {
        "workflow_type": domain,
        "current_node": "classify_objective",
    }


async def plan_execution_node(state: EmpireState) -> Dict[str, Any]:
    workflow_id = state["workflow_id"]
    domain = state["workflow_type"]

    await event_system.publish(
        event_type="AgentThinking",
        payload={"agent": "Jeffrey", "action": f"Formulating plan for {domain}"},
        agent_id="jeffrey",
        workflow_id=workflow_id,
    )

    # Tasks support explicit dependencies so independent tasks execute in parallel
    if domain == "development":
        tasks = [
            {"id": "t1", "title": "Definir Arquitetura e Contratos", "assigned_agent": "noe", "dependencies": [], "status": "pending"},
            {"id": "t2", "title": "Modelagem de Dados e Migrations", "assigned_agent": "ford", "dependencies": ["t1"], "status": "pending"},
            {"id": "t3", "title": "Desenvolver Backend FastAPI", "assigned_agent": "balsini", "dependencies": ["t1"], "status": "pending"},
            {"id": "t4", "title": "Desenvolver Frontend React", "assigned_agent": "fonseca", "dependencies": ["t1"], "status": "pending"},
            {"id": "t5", "title": "Quality Gate e Testes Automatizados", "assigned_agent": "murphy", "dependencies": ["t2", "t3", "t4"], "status": "pending"},
            {"id": "t6", "title": "Configuração de Deploy e Docker", "assigned_agent": "jarvis", "dependencies": ["t5"], "status": "pending"},
        ]
    elif domain == "content":
        tasks = [
            {"id": "t1", "title": "Pesquisa de Fontes e Tendências", "assigned_agent": "news_agent", "dependencies": [], "status": "pending"},
            {"id": "t2", "title": "Redação de Roteiro de Alta Retenção", "assigned_agent": "script_agent", "dependencies": ["t1"], "status": "pending"},
            {"id": "t3", "title": "Geração de Assets Visuais", "assigned_agent": "designer_agent", "dependencies": ["t2"], "status": "pending"},
            {"id": "t4", "title": "Geração de Narração TTS", "assigned_agent": "voice_agent", "dependencies": ["t2"], "status": "pending"},
            {"id": "t5", "title": "Transcrição e Legendas SRT", "assigned_agent": "subtitle_agent", "dependencies": ["t4"], "status": "pending"},
            {"id": "t6", "title": "Montagem Audiovisual e Render", "assigned_agent": "video_agent", "dependencies": ["t3", "t4", "t5"], "status": "pending"},
            {"id": "t7", "title": "Quality Gate de Mídia Murphy", "assigned_agent": "murphy", "dependencies": ["t6"], "status": "pending"},
        ]
    elif domain == "clip":
        req = state["user_request"].lower()
        if any(k in req for k in ["encontr", "pesquis", "busqu", "procur", "selecion"]):
            tasks = [
                {"id": "t1", "title": "Pesquisa e Triagem de Vídeos e Lives em Alta", "assigned_agent": "clipador_agent", "dependencies": [], "status": "pending"},
                {"id": "t2", "title": "Mapeamento de Melhores Momentos e Minutagem", "assigned_agent": "clipador_agent", "dependencies": ["t1"], "status": "pending"},
                {"id": "t3", "title": "Estruturação de Ganchos e Propostas de Cortes", "assigned_agent": "script_agent", "dependencies": ["t2"], "status": "pending"},
                {"id": "t4", "title": "Validação de Qualidade e Potencial Viral", "assigned_agent": "murphy", "dependencies": ["t3"], "status": "pending"},
            ]
        else:
            tasks = [
                {"id": "t1", "title": "Análise de Retenção de Vídeo", "assigned_agent": "clipador_agent", "dependencies": [], "status": "pending"},
                {"id": "t2", "title": "Extração de Cortes Candidatos", "assigned_agent": "clipador_agent", "dependencies": ["t1"], "status": "pending"},
                {"id": "t3", "title": "Legendas Dinâmicas Verticais", "assigned_agent": "subtitle_agent", "dependencies": ["t2"], "status": "pending"},
                {"id": "t4", "title": "Validação de Qualidade", "assigned_agent": "murphy", "dependencies": ["t3"], "status": "pending"},
            ]
    elif domain == "business":
        tasks = [
            {"id": "t1", "title": "Análise de Mercado e Nicho", "assigned_agent": "news_agent", "dependencies": [], "status": "pending"},
            {"id": "t2", "title": "Modelagem de Negócio e Monetização", "assigned_agent": "jeffrey", "dependencies": ["t1"], "status": "pending"},
            {"id": "t3", "title": "Arquitetura da Solução Digital", "assigned_agent": "noe", "dependencies": ["t2"], "status": "pending"},
            {"id": "t4", "title": "Plano de Lançamento e Validação", "assigned_agent": "murphy", "dependencies": ["t3"], "status": "pending"},
        ]
    else:
        tasks = [
            {"id": "t1", "title": "Análise de Viabilidade", "assigned_agent": "noe", "dependencies": [], "status": "pending"},
            {"id": "t2", "title": "Execução da Operação", "assigned_agent": "balsini", "dependencies": ["t1"], "status": "pending"},
            {"id": "t3", "title": "Revisão e Quality Gate", "assigned_agent": "murphy", "dependencies": ["t2"], "status": "pending"},
        ]

    # Allow custom injected tasks from execution_context (for testing/delegation)
    custom_tasks = (state.get("execution_context") or {}).get("custom_tasks")
    if isinstance(custom_tasks, list) and custom_tasks:
        tasks = custom_tasks

    plan = [{"step": i + 1, "description": t["title"], "agent": t["assigned_agent"]} for i, t in enumerate(tasks)]
    checkpoint_manager.save_checkpoint(workflow_id, "plan_execution", state, 2)

    return {
        "plan": plan,
        "tasks": tasks,
        "current_node": "plan_execution",
    }


async def validate_plan_node(state: EmpireState) -> Dict[str, Any]:
    requires_approval = False
    for task in state.get("tasks", []):
        t_title = task["title"].lower()
        if any(kw in t_title for kw in ("deploy", "produção", "exclusão", "lançamento")):
            requires_approval = True
            break

    return {
        "waiting_for_approval": requires_approval,
        "current_node": "validate_plan",
    }


def approval_router(state: EmpireState) -> Literal["request_approval", "execute_plan"]:
    if state.get("waiting_for_approval", False):
        return "request_approval"
    return "execute_plan"


async def request_approval_node(state: EmpireState) -> Dict[str, Any]:
    """Real LangGraph Human-in-the-Loop interrupt()."""
    workflow_id = state["workflow_id"]
    approval_id = str(uuid.uuid4())
    approval_data = {
        "id": approval_id,
        "action_name": "Deploy ou Lançamento em Produção",
        "requested_by": "Jeffrey",
        "description": "O plano inclui etapas de implantação/lançamento que exigem consentimento do proprietário.",
        "risks": ["Impacto em infraestrutura", "Visibilidade externa"],
        "status": "pending",
    }

    checkpoint_manager.save_checkpoint(workflow_id, "request_approval", state, 3)

    # Pause graph execution until human approves/rejects via Command(resume=...)
    decision = interrupt(approval_data)
    approved = bool(decision.get("approved", False)) if isinstance(decision, dict) else False
    feedback = decision.get("feedback") if isinstance(decision, dict) else None

    approval_data["status"] = "approved" if approved else "rejected"
    approval_data["feedback"] = feedback

    return {
        "approvals": [approval_data],
        "waiting_for_approval": False,
        "execution_context": {
            **(state.get("execution_context") or {}),
            "approval_decision": {"approved": approved, "feedback": feedback},
        },
        "current_node": "request_approval",
    }


def post_approval_router(state: EmpireState) -> Literal["execute_plan", "rejected_plan"]:
    decision = (state.get("execution_context") or {}).get("approval_decision", {})
    if decision.get("approved", False):
        return "execute_plan"
    return "rejected_plan"


async def rejected_plan_node(state: EmpireState) -> Dict[str, Any]:
    workflow_id = state["workflow_id"]
    feedback = ((state.get("execution_context") or {}).get("approval_decision") or {}).get("feedback", "")
    final_res = {
        "status": "rejected",
        "summary": f"Execução cancelada pelo proprietário. Feedback: {feedback or 'Sem comentários.'}",
        "artifacts": state.get("artifacts", []),
    }
    await event_system.publish(
        event_type="WorkflowRejected",
        payload=final_res,
        workflow_id=workflow_id,
    )
    return {"final_result": final_res, "current_node": "rejected_plan"}


def _build_tool_call_for_agent(agent_id: str, workflow_id: str, user_request: str) -> Dict[str, Any] | None:
    if agent_id == "script_agent":
        return {
            "tool_id": "script_generator",
            "params": {"topic": user_request, "format": "shorts"},
            "artifact_name": "Roteiro Produzido",
            "artifact_type": "script",
        }
    if agent_id == "voice_agent":
        return {
            "tool_id": "tts_generator",
            "params": {"text": "Narração oficial do roteiro"},
            "artifact_name": "Áudio de Narração",
            "artifact_type": "audio",
        }
    if agent_id == "subtitle_agent":
        return {
            "tool_id": "srt_formatter",
            "params": {},
            "artifact_name": "Legendas Sincronizadas",
            "artifact_type": "subtitle",
        }
    if agent_id in ("noe", "balsini", "fonseca", "ford", "jarvis", "designer_agent", "video_agent", "clipador_agent"):
        return {
            "tool_id": "file_writer",
            "params": {"path": f"artifacts/{agent_id}_deliverable_{workflow_id[:8]}.md"},
            "artifact_name": f"Entrega Técnica {agent_id}",
            "artifact_type": "code" if agent_id in ("balsini", "fonseca", "ford") else "document",
        }
    return None


async def execute_plan_node(state: EmpireState) -> Dict[str, Any]:
    workflow_id = state["workflow_id"]
    project_id = state.get("project_id")
    tasks = [dict(t) for t in state.get("tasks", [])]
    completed_tasks = list(state.get("completed_tasks", []))
    failed_tasks = list(state.get("failed_tasks", []))
    artifacts = list(state.get("artifacts", []))
    errors = list(state.get("errors", []))
    outputs_by_task_id: Dict[str, str] = {}
    completed_ids = {t["id"] for t in completed_tasks}

    semaphore = asyncio.Semaphore(MAX_PARALLEL_AGENTS)

    async def _run_single_task(task: Dict[str, Any]) -> Dict[str, Any]:
        async with semaphore:
            agent_id = task["assigned_agent"]
            deps = task.get("dependencies", [])
            dep_outputs = {d: outputs_by_task_id[d] for d in deps if d in outputs_by_task_id}
            tool_call = _build_tool_call_for_agent(agent_id, workflow_id, state["user_request"])

            result = await agent_executor.execute_task(
                agent_id=agent_id,
                task_title=task["title"],
                task_description=f"Objetivo: {state.get('objective') or state['user_request']}",
                workflow_id=workflow_id,
                project_id=project_id,
                user_id=(state.get("execution_context") or {}).get("user_id"),
                dependency_outputs=dep_outputs,
                tool_call=tool_call,
            )

            # Automatic agent substitution on failure if backup exists
            if result.status == "failed" and agent_id in BACKUP_AGENT_MAP:
                backup_agent = BACKUP_AGENT_MAP[agent_id]
                await event_system.publish(
                    event_type="AgentSubstituted",
                    payload={"failed_agent": agent_id, "backup_agent": backup_agent, "task": task["title"]},
                    agent_id="jeffrey",
                    workflow_id=workflow_id,
                )
                backup_tool = _build_tool_call_for_agent(backup_agent, workflow_id, state["user_request"])
                result = await agent_executor.execute_task(
                    agent_id=backup_agent,
                    task_title=f"[Contingência] {task['title']}",
                    task_description=f"Assumindo tarefa após falha de {agent_id} ({result.error}). Objetivo: {state['user_request']}",
                    workflow_id=workflow_id,
                    project_id=project_id,
                    user_id=(state.get("execution_context") or {}).get("user_id"),
                    dependency_outputs=dep_outputs,
                    tool_call=backup_tool,
                )
                task["substituted_by"] = backup_agent

            return {"task": task, "result": result}

    # Dependency-aware parallel wave execution (bounded by len(tasks) to prevent infinite loops)
    pending = [t for t in tasks if t["id"] not in completed_ids]
    waves = 0
    while pending and waves <= len(tasks) + 1:
        waves += 1
        ready = [t for t in pending if all(d in completed_ids for d in t.get("dependencies", []))]
        if not ready:
            # Deadlock / unmet dependency -> fail remaining cleanly
            for t in pending:
                t["status"] = "failed"
                failed_tasks.append(t)
                errors.append(f"Dependência não satisfeita para tarefa '{t['title']}'.")
            break

        wave_results = await asyncio.gather(*[_run_single_task(t) for t in ready])
        for item in wave_results:
            t = item["task"]
            res = item["result"]
            if res.status == "completed":
                t["status"] = "completed"
                t["output_summary"] = res.summary[:400]
                completed_tasks.append(t)
                completed_ids.add(t["id"])
                outputs_by_task_id[t["id"]] = res.summary[:500]
                artifacts.extend(res.artifacts_created)
            else:
                t["status"] = "failed"
                failed_tasks.append(t)
                errors.append(f"Agente {t['assigned_agent']} falhou em '{t['title']}': {res.error}")

        pending = [t for t in pending if t["id"] not in completed_ids and t not in failed_tasks]

    checkpoint_manager.save_checkpoint(workflow_id, "execute_plan", state, 4)

    return {
        "tasks": tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "artifacts": artifacts,
        "errors": errors,
        "current_node": "execute_plan",
    }


async def evaluate_results_node(state: EmpireState) -> Dict[str, Any]:
    artifacts = state.get("artifacts", [])
    artifact_paths = [a.get("path", "") for a in artifacts if a.get("path")]

    qa_res = await tool_registry.execute(
        "quality_scorer",
        {"artifact_paths": artifact_paths},
        "murphy",
    )

    has_failures = len(state.get("failed_tasks", [])) > 0
    quality_score = qa_res.output.get("score", 1.0) if qa_res.output else 0.0
    passed = bool(qa_res.output.get("passed", True)) and not has_failures

    quality_entry = {
        "score": quality_score,
        "passed": passed,
        "evaluated_by": "murphy",
        "artifacts_evaluated": len(artifact_paths),
        "failed_tasks": len(state.get("failed_tasks", [])),
    }

    return {
        "quality_results": [quality_entry],
        "current_node": "evaluate_results",
    }


def replan_router(state: EmpireState) -> Literal["replan", "consolidate_result"]:
    last_qa = state.get("quality_results", [{}])[-1]
    passed = last_qa.get("passed", True)
    iteration = state.get("iteration_count", 0)

    if not passed and iteration < MAX_REPLAN_ITERATIONS:
        return "replan"
    return "consolidate_result"


async def replan_node(state: EmpireState) -> Dict[str, Any]:
    workflow_id = state["workflow_id"]
    await event_system.publish(
        event_type="AgentThinking",
        payload={"agent": "Jeffrey", "action": "Re-evaluating plan due to QA/task feedback"},
        agent_id="jeffrey",
        workflow_id=workflow_id,
    )
    # Reset failed tasks to pending for retry
    updated_tasks = []
    for t in state.get("tasks", []):
        t_copy = dict(t)
        if t_copy.get("status") == "failed":
            t_copy["status"] = "pending"
        updated_tasks.append(t_copy)

    return {
        "tasks": updated_tasks,
        "failed_tasks": [],
        "iteration_count": state.get("iteration_count", 0) + 1,
        "current_node": "replan",
    }


async def consolidate_result_node(state: EmpireState) -> Dict[str, Any]:
    workflow_id = state["workflow_id"]
    completed_count = len(state.get("completed_tasks", []))
    failed_count = len(state.get("failed_tasks", []))
    artifacts_count = len(state.get("artifacts", []))

    status = "success" if failed_count == 0 else "partial_failure"
    final_summary = (
        f"Missão finalizada ({status}) sob coordenação do CEO Jeffrey. "
        f"{completed_count} tarefas concluídas, {failed_count} falhas, {artifacts_count} artefatos produzidos."
    )

    final_result = {
        "status": status,
        "summary": final_summary,
        "objective": state.get("objective"),
        "artifacts": state.get("artifacts", []),
        "completed_tasks": completed_count,
        "failed_tasks": failed_count,
    }

    await event_system.publish(
        event_type="WorkflowCompleted" if failed_count == 0 else "WorkflowCompletedWithErrors",
        payload=final_result,
        workflow_id=workflow_id,
    )

    checkpoint_manager.save_checkpoint(workflow_id, "consolidate_result", state, 5)

    return {
        "final_result": final_result,
        "current_node": "consolidate_result",
    }


def build_jeffrey_supervisor_graph():
    builder = StateGraph(EmpireState)

    builder.add_node("interpret_request", interpret_request_node)
    builder.add_node("classify_objective", classify_objective_node)
    builder.add_node("plan_execution", plan_execution_node)
    builder.add_node("validate_plan", validate_plan_node)
    builder.add_node("request_approval", request_approval_node)
    builder.add_node("rejected_plan", rejected_plan_node)
    builder.add_node("execute_plan", execute_plan_node)
    builder.add_node("evaluate_results", evaluate_results_node)
    builder.add_node("replan", replan_node)
    builder.add_node("consolidate_result", consolidate_result_node)

    builder.add_edge(START, "interpret_request")
    builder.add_edge("interpret_request", "classify_objective")
    builder.add_edge("classify_objective", "plan_execution")
    builder.add_edge("plan_execution", "validate_plan")

    builder.add_conditional_edges(
        "validate_plan",
        approval_router,
        {
            "request_approval": "request_approval",
            "execute_plan": "execute_plan",
        },
    )
    builder.add_conditional_edges(
        "request_approval",
        post_approval_router,
        {
            "execute_plan": "execute_plan",
            "rejected_plan": "rejected_plan",
        },
    )
    builder.add_edge("rejected_plan", END)
    builder.add_edge("execute_plan", "evaluate_results")

    builder.add_conditional_edges(
        "evaluate_results",
        replan_router,
        {
            "replan": "replan",
            "consolidate_result": "consolidate_result",
        },
    )
    builder.add_edge("replan", "execute_plan")
    builder.add_edge("consolidate_result", END)

    return builder.compile(checkpointer=persistent_checkpointer)


jeffrey_supervisor_graph = build_jeffrey_supervisor_graph()
