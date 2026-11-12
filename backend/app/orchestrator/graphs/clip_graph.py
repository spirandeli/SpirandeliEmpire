"""SpirandeliEmpire OS 3.1 — Clip Production LangGraph Workflow"""

import uuid
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from app.orchestrator.state.empire_state import EmpireState
from app.tools.registry import tool_registry
from app.orchestrator.checkpoints.checkpoint_manager import checkpoint_manager
from app.orchestrator.checkpoints.persistent_saver import persistent_checkpointer
from app.agents.executor import agent_executor


async def video_input_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "video_input"}


async def transcript_analysis_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "transcript_analysis"}


async def clipador_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    await agent_executor.execute_task(
        agent_id="clipador_agent",
        task_title="Detecção de Cortes Virais",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
    )
    candidates = [
        {"id": "clip_1", "start": "00:01:15", "end": "00:02:00", "hook": "A revelação surpreendente"},
        {"id": "clip_2", "start": "00:04:30", "end": "00:05:15", "hook": "O momento decisivo"},
    ]
    checkpoint_manager.save_checkpoint(wf_id, "clipador", state, 2)
    return {
        "execution_context": {**(state.get("execution_context") or {}), "candidates": candidates},
        "current_node": "clipador",
    }


async def candidate_clips_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "candidate_clips"}


async def user_approval_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    approval_data = {
        "id": str(uuid.uuid4()),
        "action_name": "Aprovação de Cortes Candidatos",
        "requested_by": "Clipador Agent",
        "description": "Selecione e aprove os cortes detectados antes da renderização.",
        "risks": ["Uso de recursos de renderização"],
        "status": "pending",
    }
    checkpoint_manager.save_checkpoint(wf_id, "user_approval", state, 3)
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
        "current_node": "user_approval",
    }


def clip_approval_router(state: EmpireState) -> Literal["clip_extraction", "rejected_delivery"]:
    decision = (state.get("execution_context") or {}).get("approval_decision", {})
    return "clip_extraction" if decision.get("approved", False) else "rejected_delivery"


async def clip_extraction_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    artifacts = list(state.get("artifacts", []))
    res = await tool_registry.execute(
        "ffmpeg_assembler",
        {"output_path": f"artifacts/extracted_clip_{wf_id[:8]}.mp4", "title": state["user_request"][:40]},
        "video_agent",
    )
    for p in res.artifacts_created:
        artifacts.append({"name": "Corte Extraído (Shorts)", "type": "video", "path": p, "creator": "video_agent"})
    return {"artifacts": artifacts, "current_node": "clip_extraction"}


async def subtitles_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    res = await agent_executor.execute_task(
        agent_id="subtitle_agent",
        task_title="Legendas Dinâmicas do Corte",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        tool_call={
            "tool_id": "srt_formatter",
            "params": {"text": state["user_request"]},
            "artifact_name": "Legendas Dinâmicas do Corte",
            "artifact_type": "subtitle",
        },
    )
    artifacts.extend(res.artifacts_created)
    return {"artifacts": artifacts, "current_node": "subtitles"}


async def rendering_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "rendering"}


async def qa_node(state: EmpireState) -> Dict[str, Any]:
    paths = [a["path"] for a in state.get("artifacts", []) if "path" in a]
    qa = await tool_registry.execute("quality_scorer", {"artifact_paths": paths}, "murphy")
    return {
        "quality_results": [{"score": qa.output.get("score", 1.0), "passed": qa.output.get("passed", True)}],
        "current_node": "qa",
    }


async def rejected_delivery_node(state: EmpireState) -> Dict[str, Any]:
    return {
        "final_result": {"status": "rejected", "summary": "Cortes rejeitados pelo proprietário.", "artifacts": []},
        "current_node": "rejected_delivery",
    }


async def delivery_node(state: EmpireState) -> Dict[str, Any]:
    final_res = {
        "status": "completed",
        "summary": "Clipagem e legendagem finalizada com cortes prontos para publicação.",
        "artifacts": state.get("artifacts", []),
    }
    return {"final_result": final_res, "current_node": "delivery"}


def build_clip_graph():
    builder = StateGraph(EmpireState)
    builder.add_node("video_input", video_input_node)
    builder.add_node("transcript_analysis", transcript_analysis_node)
    builder.add_node("clipador", clipador_node)
    builder.add_node("candidate_clips", candidate_clips_node)
    builder.add_node("user_approval", user_approval_node)
    builder.add_node("clip_extraction", clip_extraction_node)
    builder.add_node("subtitles", subtitles_node)
    builder.add_node("rendering", rendering_node)
    builder.add_node("qa", qa_node)
    builder.add_node("rejected_delivery", rejected_delivery_node)
    builder.add_node("delivery", delivery_node)

    builder.add_edge(START, "video_input")
    builder.add_edge("video_input", "transcript_analysis")
    builder.add_edge("transcript_analysis", "clipador")
    builder.add_edge("clipador", "candidate_clips")
    builder.add_edge("candidate_clips", "user_approval")
    builder.add_conditional_edges(
        "user_approval",
        clip_approval_router,
        {"clip_extraction": "clip_extraction", "rejected_delivery": "rejected_delivery"},
    )
    builder.add_edge("clip_extraction", "subtitles")
    builder.add_edge("subtitles", "rendering")
    builder.add_edge("rendering", "qa")
    builder.add_edge("qa", "delivery")
    builder.add_edge("rejected_delivery", END)
    builder.add_edge("delivery", END)

    return builder.compile(checkpointer=persistent_checkpointer)


clip_graph = build_clip_graph()
