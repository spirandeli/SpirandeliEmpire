"""
Worker assíncrono ABVOS para ARQ e Redis.
Executa tarefas de longa duração e renderização multimídia sem timeout (Timeout Infinite).
"""
import logging
from typing import Optional
from arq.connections import RedisSettings
from arq.worker import func

from src.config import get_settings
from src.services.media.pipeline import (
    execute_full_video_pipeline,
    execute_full_media_pipeline,
    router,
)

logger = logging.getLogger("abvos.worker")
settings = get_settings()


class WorkerSettings:
    """
    Configuração oficial do Worker ARQ / ABVOS:
    - job_timeout = None: Desativa qualquer limite de tempo (Timeout Infinite).
    - Permite processamento sequencial garantido das 20 cenas e compilação FFmpeg sem interrupção.
    """
    functions = [
        func(
            execute_full_video_pipeline,
            name="execute_full_video_pipeline",
            timeout=None,  # Timeout Infinite
            keep_result=3600,
        ),
        func(
            execute_full_media_pipeline,
            name="execute_full_media_pipeline",
            timeout=None,  # Timeout Infinite
            keep_result=3600,
        ),
    ]
    job_timeout: Optional[int] = None  # Desativa timeout global no ARQ
    max_jobs: int = 10
    redis_settings: RedisSettings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
    )


if __name__ == "__main__":
    from arq import run_worker
    logger.info("Iniciando Worker ARQ ABVOS com job_timeout=None...")
    run_worker(WorkerSettings)

