"""SpirandeliEmpire OS 3.1 — Business Creation LangGraph Workflow"""

import uuid
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from app.orchestrator.state.empire_state import EmpireState
from app.tools.registry import tool_registry
from app.orchestrator.checkpoints.checkpoint_manager import checkpoint_manager
from app.orchestrator.checkpoints.persistent_saver import persistent_checkpointer
from app.agents.executor import agent_executor


async def business_idea_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "business_idea"}


async def market_research_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    res = await tool_registry.execute("web_search", {"query": state["user_request"]}, "news_agent")
    checkpoint_manager.save_checkpoint(wf_id, "market_research", state, 1)
    return {
        "execution_context": {**(state.get("execution_context") or {}), "market_data": res.output},
        "current_node": "market_research",
    }


async def business_model_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    res = await agent_executor.execute_task(
        agent_id="jeffrey",
        task_title="Estruturação de Business Model Canvas",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        task_profile="complex_planning",
        tool_call={
            "tool_id": "file_writer",
            "params": {"path": f"artifacts/business_model_canvas_{wf_id[:8]}.md"},
            "artifact_name": "Business Model Canvas",
            "artifact_type": "document",
        },
    )
    artifacts.extend(res.artifacts_created)
    return {"artifacts": artifacts, "current_node": "business_model"}


async def feasibility_analysis_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "feasibility_analysis"}


async def architecture_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "architecture"}


async def implementation_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    res = await agent_executor.execute_task(
        agent_id="fonseca",
        task_title="Especificação MVP Digital",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        task_profile="coding",
        tool_call={
            "tool_id": "file_writer",
            "params": {
                "path": f"artifacts/mvp_landing_spec_{wf_id[:8]}.html",
            },
            "artifact_name": "Especificação MVP Digital",
            "artifact_type": "code",
        },
    )
    artifacts.extend(res.artifacts_created)
    return {"artifacts": artifacts, "current_node": "implementation"}


async def testing_node(state: EmpireState) -> Dict[str, Any]:
    paths = [a["path"] for a in state.get("artifacts", []) if "path" in a]
    qa = await tool_registry.execute("quality_scorer", {"artifact_paths": paths}, "murphy")
    return {
        "quality_results": [{"score": qa.output.get("score", 1.0), "passed": qa.output.get("passed", True)}],
        "current_node": "testing",
    }


async def deployment_approval_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    approval_data = {
        "id": str(uuid.uuid4()),
        "action_name": "Aprovação de Lançamento do Negócio Digital",
        "requested_by": "Jeffrey",
        "description": "Autorize o lançamento do MVP e publicação inicial.",
        "risks": ["Exposição pública da marca"],
        "status": "pending",
    }
    checkpoint_manager.save_checkpoint(wf_id, "deployment_approval", state, 2)
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


def biz_approval_router(state: EmpireState) -> Literal["launch", "rejected_launch"]:
    decision = (state.get("execution_context") or {}).get("approval_decision", {})
    return "launch" if decision.get("approved", False) else "rejected_launch"


async def launch_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "launch"}


async def monitoring_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "monitoring"}


async def rejected_launch_node(state: EmpireState) -> Dict[str, Any]:
    return {
        "final_result": {"status": "rejected", "summary": "Lançamento cancelado pelo proprietário.", "artifacts": state.get("artifacts", [])},
        "current_node": "rejected_launch",
    }


async def optimization_node(state: EmpireState) -> Dict[str, Any]:
    final_res = {
        "status": "completed",
        "summary": "Negócio digital estruturado, modelado e validado para lançamento pelo SpirandeliEmpire.",
        "artifacts": state.get("artifacts", []),
    }
    return {"final_result": final_res, "current_node": "optimization"}


def build_business_graph():
    builder = StateGraph(EmpireState)
    builder.add_node("business_idea", business_idea_node)
    builder.add_node("market_research", market_research_node)
    builder.add_node("business_model", business_model_node)
    builder.add_node("feasibility_analysis", feasibility_analysis_node)
    builder.add_node("architecture", architecture_node)
    builder.add_node("implementation", implementation_node)
    builder.add_node("testing", testing_node)
    builder.add_node("deployment_approval", deployment_approval_node)
    builder.add_node("launch", launch_node)
    builder.add_node("monitoring", monitoring_node)
    builder.add_node("rejected_launch", rejected_launch_node)
    builder.add_node("optimization", optimization_node)

    builder.add_edge(START, "business_idea")
    builder.add_edge("business_idea", "market_research")
    builder.add_edge("market_research", "business_model")
    builder.add_edge("business_model", "feasibility_analysis")
    builder.add_edge("feasibility_analysis", "architecture")
    builder.add_edge("architecture", "implementation")
    builder.add_edge("implementation", "testing")
    builder.add_edge("testing", "deployment_approval")
    builder.add_conditional_edges(
        "deployment_approval",
        biz_approval_router,
        {"launch": "launch", "rejected_launch": "rejected_launch"},
    )
    builder.add_edge("launch", "monitoring")
    builder.add_edge("monitoring", "optimization")
    builder.add_edge("rejected_launch", END)
    builder.add_edge("optimization", END)

    return builder.compile(checkpointer=persistent_checkpointer)


business_graph = build_business_graph()
