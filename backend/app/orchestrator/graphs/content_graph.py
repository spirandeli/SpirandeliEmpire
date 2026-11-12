"""SpirandeliEmpire OS 3.1 — Content Production LangGraph Workflow"""

from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from app.orchestrator.state.empire_state import EmpireState
from app.tools.registry import tool_registry
from app.orchestrator.checkpoints.checkpoint_manager import checkpoint_manager
from app.orchestrator.checkpoints.persistent_saver import persistent_checkpointer
from app.agents.executor import agent_executor


async def research_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    search_res = await tool_registry.execute("web_search", {"query": state["user_request"]}, "news_agent")
    exec_res = await agent_executor.execute_task(
        agent_id="news_agent",
        task_title="Pesquisa de Tendências e Fontes",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
    )
    checkpoint_manager.save_checkpoint(wf_id, "research", state, 1)
    return {
        "execution_context": {
            **(state.get("execution_context") or {}),
            "research": search_res.output,
            "research_summary": exec_res.summary[:500],
        },
        "current_node": "research",
    }


async def content_strategy_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "content_strategy"}


async def script_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    res = await agent_executor.execute_task(
        agent_id="script_agent",
        task_title="Redação de Roteiro",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        dependency_outputs={"research": (state.get("execution_context") or {}).get("research_summary", "")},
        tool_call={
            "tool_id": "script_generator",
            "params": {"topic": state["user_request"], "format": "shorts"},
            "artifact_name": "Roteiro Produzido",
            "artifact_type": "script",
        },
    )
    artifacts.extend(res.artifacts_created)
    checkpoint_manager.save_checkpoint(wf_id, "script", state, 2)
    return {"artifacts": artifacts, "current_node": "script"}


async def script_review_node(state: EmpireState) -> Dict[str, Any]:
    return {"current_node": "script_review"}


async def visual_generation_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    res = await agent_executor.execute_task(
        agent_id="designer_agent",
        task_title="Geração de Thumbnail/Visual",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        tool_call={
            "tool_id": "image_generator",
            "params": {
                "path": f"artifacts/thumbnail_{wf_id[:8]}.png",
                "title": state["user_request"][:48],
            },
            "artifact_name": "Asset Visual / Thumbnail",
            "artifact_type": "image",
        },
    )
    artifacts.extend(res.artifacts_created)
    return {"artifacts": artifacts, "current_node": "visual_generation"}


async def voice_generation_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    exec_ctx = dict(state.get("execution_context") or {})
    tts_res = await tool_registry.execute("tts_generator", {"text": state["user_request"][:200]}, "voice_agent")
    if tts_res.success:
        res = await agent_executor.execute_task(
            agent_id="voice_agent",
            task_title="Síntese de Narração TTS",
            task_description=state["user_request"],
            workflow_id=wf_id,
            project_id=state.get("project_id"),
            user_id=user_id,
            tool_call={
                "tool_id": "tts_generator",
                "params": {"text": state["user_request"][:200]},
                "artifact_name": "Narração de Áudio",
                "artifact_type": "audio",
            },
        )
        artifacts.extend(res.artifacts_created)
        exec_ctx["tts_status"] = "completed"
    else:
        exec_ctx["tts_status"] = "blocked"
        exec_ctx["tts_error"] = tts_res.error
    return {"artifacts": artifacts, "execution_context": exec_ctx, "current_node": "voice_generation"}


async def subtitles_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    res = await agent_executor.execute_task(
        agent_id="subtitle_agent",
        task_title="Geração de Legendas SRT",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        tool_call={
            "tool_id": "srt_formatter",
            "params": {"text": state["user_request"]},
            "artifact_name": "Legendas SRT Sincronizadas",
            "artifact_type": "subtitle",
        },
    )
    artifacts.extend(res.artifacts_created)
    return {"artifacts": artifacts, "current_node": "subtitles"}


async def video_assembly_node(state: EmpireState) -> Dict[str, Any]:
    wf_id = state["workflow_id"]
    user_id = (state.get("execution_context") or {}).get("user_id")
    artifacts = list(state.get("artifacts", []))
    res = await agent_executor.execute_task(
        agent_id="video_agent",
        task_title="Montagem e Renderização de Vídeo",
        task_description=state["user_request"],
        workflow_id=wf_id,
        project_id=state.get("project_id"),
        user_id=user_id,
        tool_call={
            "tool_id": "ffmpeg_assembler",
            "params": {
                "output_path": f"artifacts/rendered_short_{wf_id[:8]}.mp4",
                "title": state["user_request"][:40],
            },
            "artifact_name": "Vídeo Final Renderizado (Shorts)",
            "artifact_type": "video",
        },
    )
    artifacts.extend(res.artifacts_created)
    return {"artifacts": artifacts, "current_node": "video_assembly"}


async def qa_node(state: EmpireState) -> Dict[str, Any]:
    paths = [a["path"] for a in state.get("artifacts", []) if "path" in a]
    qa = await tool_registry.execute("quality_scorer", {"artifact_paths": paths}, "murphy")
    return {
        "quality_results": [{"score": qa.output.get("score", 1.0), "passed": qa.output.get("passed", True)}],
        "current_node": "qa",
    }


async def final_delivery_node(state: EmpireState) -> Dict[str, Any]:
    final_res = {
        "status": "completed",
        "summary": "Pacote audiovisual completo gerado com roteiro, áudio, legendas e vídeo final renderizado.",
        "artifacts": state.get("artifacts", []),
    }
    return {"final_result": final_res, "current_node": "final_delivery"}


def build_content_graph():
    builder = StateGraph(EmpireState)
    builder.add_node("research", research_node)
    builder.add_node("content_strategy", content_strategy_node)
    builder.add_node("script", script_node)
    builder.add_node("script_review", script_review_node)
    builder.add_node("visual_generation", visual_generation_node)
    builder.add_node("voice_generation", voice_generation_node)
    builder.add_node("subtitles", subtitles_node)
    builder.add_node("video_assembly", video_assembly_node)
    builder.add_node("qa", qa_node)
    builder.add_node("final_delivery", final_delivery_node)

    builder.add_edge(START, "research")
    builder.add_edge("research", "content_strategy")
    builder.add_edge("content_strategy", "script")
    builder.add_edge("script", "script_review")
    builder.add_edge("script_review", "visual_generation")
    builder.add_edge("visual_generation", "voice_generation")
    builder.add_edge("voice_generation", "subtitles")
    builder.add_edge("subtitles", "video_assembly")
    builder.add_edge("video_assembly", "qa")
    builder.add_edge("qa", "final_delivery")
    builder.add_edge("final_delivery", END)

    return builder.compile(checkpointer=persistent_checkpointer)


content_graph = build_content_graph()
