"""SpirandeliEmpire OS 3.1 — LangGraph Empire State Definition"""

from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TaskItem(BaseModel):
    id: str
    title: str
    assigned_agent: str
    status: str = "pending"  # pending, in_progress, completed, failed
    dependencies: List[str] = Field(default_factory=list)
    output: Optional[Any] = None
    error: Optional[str] = None


class ArtifactItem(BaseModel):
    id: str
    name: str
    type: str
    path: str
    size: int = 0
    creator_agent: str


class ApprovalItem(BaseModel):
    id: str
    action_name: str
    requested_by: str
    description: str
    risks: List[str] = Field(default_factory=list)
    status: str = "pending"  # pending, approved, rejected
    feedback: Optional[str] = None


class QualityCheckResult(BaseModel):
    step_name: str
    score: float
    passed: bool
    evidence: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class EmpireState(TypedDict):
    """
    Central LangGraph State for SpirandeliEmpire workflows.
    Designed carefully to stay compact and only reference artifact paths.
    """
    workflow_id: str
    project_id: Optional[str]
    workflow_type: str  # supervisor, development, content, clip, business
    user_request: str
    objective: str
    plan: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    active_agents: List[str]
    completed_tasks: List[Dict[str, Any]]
    failed_tasks: List[Dict[str, Any]]
    artifacts: List[Dict[str, Any]]
    approvals: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    execution_context: Dict[str, Any]
    quality_results: List[Dict[str, Any]]
    errors: List[str]
    final_result: Optional[Dict[str, Any]]
    current_node: str
    iteration_count: int
    waiting_for_approval: bool


def create_initial_state(
    workflow_id: str,
    user_request: str,
    project_id: Optional[str] = None,
    workflow_type: str = "supervisor",
    context: Optional[Dict[str, Any]] = None
) -> EmpireState:
    return {
        "workflow_id": workflow_id,
        "project_id": project_id,
        "workflow_type": workflow_type,
        "user_request": user_request,
        "objective": "",
        "plan": [],
        "tasks": [],
        "active_agents": ["jeffrey"],
        "completed_tasks": [],
        "failed_tasks": [],
        "artifacts": [],
        "approvals": [],
        "messages": [
            {"sender": "user", "text": user_request}
        ],
        "execution_context": context or {},
        "quality_results": [],
        "errors": [],
        "final_result": None,
        "current_node": "start",
        "iteration_count": 0,
        "waiting_for_approval": False
    }

