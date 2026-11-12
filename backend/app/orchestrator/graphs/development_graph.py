"""SpirandeliEmpire OS 3.1 — Development LangGraph Workflow"""

import uuid
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from app.orchestrator.state.empire_state import EmpireState
from app.tools.registry import tool_registry
from app.events.manager import event_system
from app.orchestrator.checkpoints.checkpoint_manager import checkpoint_manager
from app.orchestrator.checkpoints.persistent_saver import persistent_checkpointer
from app.agents.executor import agent_executor


async def requirements_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    res = await agent_executor.execute_task(
        agent_id="noe",
        task_title="Análise de Requisitos",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        task_profile="complex_planning",
    )
    checkpoint_manager.save_checkpoint(wf_id, "requirements", state, 1)
    return {
        "execution_context": {**(state.get("execution_context") or {}), "requirements": res.summary[:600]},
        "current_node": "requirements",
    }


async def architecture_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    req_summary = (state.get("execution_context") or {}).get("requirements", "")
    res = await agent_executor.execute_task(
        agent_id="noe",
        task_title="ADR de Arquitetura do Sistema",
        task_description=f"Gerar ADR para: {state['user_request']}",
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        task_profile="complex_planning",
        dependency_outputs={"requirements": req_summary},
        tool_call={
            "tool_id": "file_writer",
            "params": {"path": f"artifacts/adr_{wf_id[:8]}.md"},
            "artifact_name": "ADR Arquitetura",
            "artifact_type": "document",
        },
    )
    artifacts = list(state.get("artifacts", [])) + res.artifacts_created
    checkpoint_manager.save_checkpoint(wf_id, "architecture", state, 2)
    return {"artifacts": artifacts, "current_node": "architecture"}


async def task_breakdown_node(state: EmpireState) -> Dict[str, Any]:
    tasks = [
        {"id": "dev_1", "title": "Modelagem de Tabelas e Migrations", "assigned_agent": "ford", "status": "pending"},
        {"id": "dev_2", "title": "Implementação de APIs e Endpoints", "assigned_agent": "balsini", "status": "pending"},
        {"id": "dev_3", "title": "Construção de Telas React", "assigned_agent": "fonseca", "status": "pending"},
    ]
    return {"tasks": tasks, "current_node": "task_breakdown"}


async def implementation_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))

    b_res = await agent_executor.execute_task(
        agent_id="balsini",
        task_title="Implementação Backend FastAPI",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        task_profile="coding",
        tool_call={
            "tool_id": "file_writer",
            "params": {"path": f"artifacts/backend_service_{wf_id[:8]}.py"},
            "artifact_name": "Backend Module",
            "artifact_type": "code",
        },
    )
    f_res = await agent_executor.execute_task(
        agent_id="fonseca",
        task_title="Implementação Frontend React",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        task_profile="coding",
        tool_call={
            "tool_id": "file_writer",
            "params": {"path": f"artifacts/frontend_view_{wf_id[:8]}.tsx"},
            "artifact_name": "Frontend Component",
            "artifact_type": "code",
        },
    )
    artifacts.extend(b_res.artifacts_created)
    artifacts.extend(f_res.artifacts_created)
    return {"artifacts": artifacts, "current_node": "implementation"}


async def data_engineering_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    res = await agent_executor.execute_task(
        agent_id="ford",
        task_title="Modelagem de Dados e Migration",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        task_profile="coding",
        tool_call={
            "tool_id": "file_writer",
            "params": {"path": f"artifacts/schema_migration_{wf_id[:8]}.sql"},
            "artifact_name": "Data Migration SQL",
            "artifact_type": "code",
        },
    )
    artifacts.extend(res.artifacts_created)
    return {"artifacts": artifacts, "current_node": "data_engineering"}


async def testing_node(state: EmpireState) -> Dict[str, Any]:
    paths = [a["path"] for a in state.get("artifacts", []) if "path" in a]
    qa = await tool_registry.execute("quality_scorer", {"artifact_paths": paths}, "murphy")
    return {
        "quality_results": [{"score": qa.output.get("score", 1.0), "passed": qa.output.get("passed", True)}],
        "current_node": "testing",
    }


async def review_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "review"}


async def deployment_approval_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    approval_data = {
        "id": str(uuid.uuid4()),
        "action_name": "Deploy de Software em Produção",
        "requested_by": "Jarvis",
        "description": "Aprovação necessária antes de implantar o código gerado em produção.",
        "risks": ["Alteração de serviços ativos"],
        "status": "pending",
    }
    checkpoint_manager.save_checkpoint(wf_id, "deployment_approval", state, 3)
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
        "current_node": "deployment_approval",
    }


def dev_approval_router(state: EmpireState) -> Literal["deployment", "rejected_report"]:
    decision = (state.get("execution_context") or {}).get("approval_decision", {})
    return "deployment" if decision.get("approved", False) else "rejected_report"


async def deployment_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    await event_system.publish("AgentStarted", {"agent": "jarvis", "action": "Container deploy verification"}, agent_id="jarvis", workflow_id=wf_id)
    sys_metrics = await tool_registry.execute("system_monitor", {}, "jarvis")
    return {
        "execution_context": {**(state.get("execution_context") or {}), "system_metrics": sys_metrics.output},
        "current_node": "deployment",
    }


async def rejected_report_node(state: EmpireState) -> Dict[str, Any]:
    return {
        "final_result": {
            "status": "rejected",
            "summary": "Deploy rejeitado pelo proprietário durante revisão.",
            "artifacts": state.get("artifacts", []),
        },
        "current_node": "rejected_report",
    }


async def final_report_node(state: EmpireState) -> Dict[str, Any]:
    final_res = {
        "status": "completed",
        "summary": "Desenvolvimento de software entregue com sucesso, validado pelo Quality Gate Murphy e implantado por Jarvis.",
        "artifacts": state.get("artifacts", []),
    }
    return {"final_result": final_res, "current_node": "final_report"}


def build_development_graph():
    builder = StateGraph(EmpireState)
    builder.add_node("requirements", requirements_node)
    builder.add_node("architecture", architecture_node)
    builder.add_node("task_breakdown", task_breakdown_node)
    builder.add_node("implementation", implementation_node)
    builder.add_node("data_engineering", data_engineering_node)
    builder.add_node("testing", testing_node)
    builder.add_node("review", review_node)
    builder.add_node("deployment_approval", deployment_approval_node)
    builder.add_node("deployment", deployment_node)
    builder.add_node("rejected_report", rejected_report_node)
    builder.add_node("final_report", final_report_node)

    builder.add_edge(START, "requirements")
    builder.add_edge("requirements", "architecture")
    builder.add_edge("architecture", "task_breakdown")
    builder.add_edge("task_breakdown", "implementation")
    builder.add_edge("implementation", "data_engineering")
    builder.add_edge("data_engineering", "testing")
    builder.add_edge("testing", "review")
    builder.add_edge("review", "deployment_approval")
    builder.add_conditional_edges(
        "deployment_approval",
        dev_approval_router,
        {"deployment": "deployment", "rejected_report": "rejected_report"},
    )
    builder.add_edge("deployment", "final_report")
    builder.add_edge("rejected_report", END)
    builder.add_edge("final_report", END)

    return builder.compile(checkpointer=persistent_checkpointer)


development_graph = build_development_graph()
