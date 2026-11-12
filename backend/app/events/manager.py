"""SpirandeliEmpire OS 3.1 — Event System, Redis Pub/Sub & WebSocket Hub"""

import json
import asyncio
from typing import Dict, Any, Set, Optional
from datetime import datetime, timezone
from fastapi import WebSocket
import redis.asyncio as aioredis
from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import EventModel

EVENTS_CHANNEL = "spirandeli:events"


class EventSystem:
    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._subscriber_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._active_connections.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._active_connections.discard(websocket)

    async def start_redis_listener(self):
        """Subscribe to Redis Pub/Sub so Celery workers can stream events to WebSockets."""
        if self._subscriber_task and not self._subscriber_task.done():
            return

        async def _listen():
            try:
                client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                pubsub = client.pubsub()
                await pubsub.subscribe(EVENTS_CHANNEL)
                async for message in pubsub.listen():
                    if message.get("type") == "message":
                        await self._broadcast_local(message["data"])
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[EventSystem] Redis Pub/Sub listener stopped: {e}")

        self._subscriber_task = asyncio.create_task(_listen())

    async def stop_redis_listener(self):
        if self._subscriber_task and not self._subscriber_task.done():
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass

    async def _broadcast_local(self, message_text: str):
        async with self._lock:
            dead_connections = []
            for ws in self._active_connections:
                try:
                    await ws.send_text(message_text)
                except Exception:
                    dead_connections.append(ws)
            for ws in dead_connections:
                self._active_connections.discard(ws)

    async def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        project_id: Optional[str] = None,
        persist: bool = True
    ) -> Dict[str, Any]:
        """Persist event to DB, publish to Redis Pub/Sub (or local WS fallback)."""
        event_data = {
            "event_type": event_type,
            "agent_id": agent_id,
            "workflow_id": workflow_id,
            "project_id": project_id,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if persist:
            try:
                async with AsyncSessionLocal() as session:
                    db_event = EventModel(
                        event_type=event_type,
                        agent_id=agent_id,
                        workflow_id=workflow_id,
                        project_id=project_id,
                        payload=payload
                    )
                    session.add(db_event)
                    await session.commit()
                    event_data["id"] = db_event.id
            except Exception as e:
                print(f"Error persisting event {event_type}: {e}")

        message_text = json.dumps(event_data)

        # Publish via Redis if listener is active, otherwise broadcast locally
        published_to_redis = False
        if self._subscriber_task and not self._subscriber_task.done():
            try:
                client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                await client.publish(EVENTS_CHANNEL, message_text)
                await client.aclose()
                published_to_redis = True
            except Exception:
                published_to_redis = False

        if not published_to_redis:
            await self._broadcast_local(message_text)

        return event_data


event_system = EventSystem()
