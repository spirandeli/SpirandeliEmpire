"""SpirandeliEmpire OS 3.1 — Durable File-Backed LangGraph Checkpointer"""

import pickle
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple
from langgraph.checkpoint.base import (
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig
from app.core.config import settings


class PersistentCheckpointSaver(InMemorySaver):
    """
    Extends LangGraph's InMemorySaver with atomic per-thread disk persistence
    so interrupted/paused workflows survive process restarts.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        super().__init__()
        self.storage_dir = storage_dir or settings.CHECKPOINTS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_threads: set[str] = set()

    def _thread_file(self, thread_id: str) -> Path:
        safe_id = "".join(c for c in thread_id if c.isalnum() or c in "-_")
        return self.storage_dir / f"{safe_id}.lgckpt.pkl"

    def _ensure_loaded(self, thread_id: str) -> None:
        if thread_id in self._loaded_threads:
            return
        self._loaded_threads.add(thread_id)
        path = self._thread_file(thread_id)
        if not path.exists():
            return
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            for ns, ckpts in data.get("storage", {}).items():
                self.storage[thread_id][ns].update(ckpts)
            for wk, wv in data.get("writes", {}).items():
                self.writes[wk] = wv
            for bk, bv in data.get("blobs", {}).items():
                self.blobs[bk] = bv
        except Exception as e:
            print(f"[PersistentCheckpointSaver] Failed to load thread {thread_id}: {e}")

    def _persist_thread(self, thread_id: str) -> None:
        path = self._thread_file(thread_id)
        tmp_path = path.with_suffix(".pkl.tmp")
        thread_storage = {
            ns: dict(ckpts) for ns, ckpts in self.storage.get(thread_id, {}).items()
        }
        thread_writes = {
            k: v for k, v in self.writes.items() if k[0] == thread_id
        }
        thread_blobs = {
            k: v for k, v in self.blobs.items() if k[0] == thread_id
        }
        payload = {
            "storage": thread_storage,
            "writes": thread_writes,
            "blobs": thread_blobs,
        }
        with open(tmp_path, "wb") as f:
            pickle.dump(payload, f)
        tmp_path.replace(path)

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        self._ensure_loaded(thread_id)
        return super().get_tuple(config)

    def list(
        self,
        config: Optional[RunnableConfig],
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        if config and "configurable" in config and "thread_id" in config["configurable"]:
            self._ensure_loaded(config["configurable"]["thread_id"])
        return super().list(config, filter=filter, before=before, limit=limit)

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        self._ensure_loaded(thread_id)
        res = super().put(config, checkpoint, metadata, new_versions)
        self._persist_thread(thread_id)
        return res

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        self._ensure_loaded(thread_id)
        super().put_writes(config, writes, task_id, task_path=task_path)
        self._persist_thread(thread_id)


persistent_checkpointer = PersistentCheckpointSaver()

