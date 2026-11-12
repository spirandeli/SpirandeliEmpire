"""SpirandeliEmpire OS 3.1 — System, Logs, Settings & VPS Monitoring Service"""

import time
from typing import Dict, Any, List, Optional
import psutil
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import SystemLogModel, SettingModel

_start_time = time.time()
# Prime psutil non-blocking cpu_percent
psutil.cpu_percent(interval=None)


class SystemService:
    def get_vps_metrics(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime_sec = int(time.time() - _start_time)

        return {
            "uptime_seconds": uptime_sec,
            "cpu": {
                "percent": cpu_percent,
                "cores_logical": psutil.cpu_count(logical=True),
                "cores_physical": psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True)
            },
            "memory": {
                "total_mb": round(mem.total / (1024 * 1024), 2),
                "used_mb": round(mem.used / (1024 * 1024), 2),
                "available_mb": round(mem.available / (1024 * 1024), 2),
                "percent": mem.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                "used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
                "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                "percent": disk.percent
            },
            "active_processes": len(psutil.pids()),
            "status": "healthy"
        }

    async def write_log(
        self,
        level: str,
        source: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> None:
        try:
            async with AsyncSessionLocal() as session:
                session.add(
                    SystemLogModel(
                        level=level.upper(),
                        source=source,
                        message=message,
                        details_json=details or {},
                        workflow_id=workflow_id,
                        agent_id=agent_id,
                    )
                )
                await session.commit()
        except Exception as e:
            print(f"[SystemService] Failed to persist log: {e}")

    async def list_logs(
        self, level: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            query = select(SystemLogModel)
            if level:
                query = query.where(SystemLogModel.level == level.upper())
            res = await session.execute(
                query.order_by(SystemLogModel.created_at.desc()).offset(offset).limit(limit)
            )
            return [
                {
                    "id": log.id,
                    "level": log.level,
                    "source": log.source,
                    "message": log.message,
                    "details": log.details_json or {},
                    "workflow_id": log.workflow_id,
                    "agent_id": log.agent_id,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in res.scalars().all()
            ]

    async def get_settings(self) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(SettingModel))
            return {
                s.key: {"value": s.value_json, "description": s.description}
                for s in res.scalars().all()
            }

    async def upsert_setting(
        self, key: str, value: Dict[str, Any], description: str = ""
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            setting = await session.get(SettingModel, key)
            if setting:
                setting.value_json = value
                if description:
                    setting.description = description
            else:
                setting = SettingModel(key=key, value_json=value, description=description)
                session.add(setting)
            await session.commit()
            return {"key": setting.key, "value": setting.value_json, "description": setting.description}


system_service = SystemService()
