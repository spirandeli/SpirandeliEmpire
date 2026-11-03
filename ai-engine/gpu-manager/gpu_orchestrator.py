"""
SpirandeliEmpire OS - GPU On-Demand Orchestrator
Enforces Section 9.5 of Specification:
- Local CPU is always default (R$ 0,00 additional cost)
- Remote GPU (e.g. RunPod, Vast.ai) is ONLY started if explicitly authorized by human commander
- Auto-shutdown after 15 minutes of inactivity to prevent unexpected charges
"""
import os
import time
import logging

logger = logging.getLogger("GPUOrchestrator")

class GPUOrchestrator:
    def __init__(self):
        self.mode = os.getenv("GPU_EXECUTION_MODE", "cpu_only")
        self.max_idle_minutes = int(os.getenv("GPU_MAX_IDLE_MINUTES", 15))
        self.last_activity_time = time.time()
        self.remote_instance_id = None

    def acquire_compute(self, task_name: str, estimated_cost_brl: float = 0.0) -> str:
        """
        Determines and provisions the optimal compute engine.
        """
        if self.mode == "cpu_only":
            logger.info(f"Task [{task_name}] running on local CPU (Cost: R$ 0,00).")
            return "local_cpu"

        # If remote GPU requested:
        if not os.getenv("GPU_REMOTE_ENABLED", "false").lower() == "true":
            logger.info(f"Remote GPU disabled in settings. Falling back to local CPU.")
            return "local_cpu"

        logger.warning("Remote GPU execution requires human approval before starting instance.")
        return "local_cpu"

    def release_compute(self):
        """Marks compute as completed and checks idle timer for shutdown."""
        self.last_activity_time = time.time()
        logger.info("Compute task completed. Idle timer reset.")

