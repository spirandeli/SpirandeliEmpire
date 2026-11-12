"""SpirandeliEmpire OS 3.1 — Checkpoint Manager for Durable Workflows"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.core.config import settings


class CheckpointManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or settings.CHECKPOINTS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, workflow_id: str) -> Path:
        return self.storage_dir / f"{workflow_id}_checkpoints.json"

    def save_checkpoint(
        self,
        workflow_id: str,
        node_name: str,
        state: Dict[str, Any],
        step_number: int
    ) -> Dict[str, Any]:
        """Persist state checkpoint for durable resumption."""
        checkpoint_entry = {
            "workflow_id": workflow_id,
            "node_name": node_name,
            "step_number": step_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state_snapshot": {
                "current_node": state.get("current_node"),
                "tasks_count": len(state.get("tasks", [])),
                "completed_tasks": len(state.get("completed_tasks", [])),
                "artifacts_count": len(state.get("artifacts", [])),
                "waiting_for_approval": state.get("waiting_for_approval", False),
                "errors": state.get("errors", [])
            }
        }

        path = self._get_path(workflow_id)
        history: List[Dict[str, Any]] = []
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append(checkpoint_entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

        return checkpoint_entry

    def get_checkpoints(self, workflow_id: str) -> List[Dict[str, Any]]:
        path = self._get_path(workflow_id)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


checkpoint_manager = CheckpointManager()
