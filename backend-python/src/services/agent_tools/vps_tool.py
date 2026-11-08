import time
from typing import Any
import psutil


def get_vps_telemetry() -> dict[str, Any]:
    """Obtém a telemetria do sistema operacional do host/VPS: CPU, RAM, disco, load average e uptime.

    Returns:
        Um dicionário com as métricas em tempo real de hardware e sistema operacional.
    """
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count(logical=True)
    vmem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Load average (1m, 5m, 15m)
    try:
        load_avg = psutil.getloadavg()
    except (AttributeError, OSError):
        load_avg = (0.0, 0.0, 0.0)

    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m"

    return {
        "status": "healthy" if cpu_percent < 85 and vmem.percent < 90 else "warning",
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count,
            "load_average_1m": round(load_avg[0], 2),
            "load_average_5m": round(load_avg[1], 2),
            "load_average_15m": round(load_avg[2], 2),
        },
        "memory": {
            "percent": vmem.percent,
            "used_mb": round(vmem.used / (1024 * 1024), 1),
            "total_mb": round(vmem.total / (1024 * 1024), 1),
            "available_mb": round(vmem.available / (1024 * 1024), 1),
        },
        "disk": {
            "percent": disk.percent,
            "used_gb": round(disk.used / (1024 * 1024 * 1024), 1),
            "total_gb": round(disk.total / (1024 * 1024 * 1024), 1),
            "free_gb": round(disk.free / (1024 * 1024 * 1024), 1),
        },
        "uptime": uptime_str,
        "uptime_seconds": uptime_seconds,
    }

