"""SpirandeliEmpire OS 3.1 — FastAPI Application Entrypoint"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import redis.asyncio as aioredis
from app.core.config import settings
from app.database.session import engine, Base, AsyncSessionLocal
from app.api.v1.api import api_router
from app.auth.dependencies import seed_default_owner_if_needed
from app.services.agent_service import agent_service
from app.services.integration_service import integration_service
from app.services.system_service import system_service
from app.events.manager import event_system


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_default_owner_if_needed()
    await agent_service.seed_agents_if_needed()
    await integration_service.seed_integrations_if_needed()
    await event_system.start_redis_listener()
    print(f"[{settings.PROJECT_NAME} v{settings.VERSION}] Core services initialized successfully.")
    yield
    await event_system.stop_redis_listener()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous AI Digital Company — LangGraph Edition",
    lifespan=lifespan,
)

# Explicit CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    await system_service.write_log(
        level="ERROR",
        source="fastapi",
        message=f"Unhandled error on {request.method} {request.url.path}: {exc}",
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Mount API v1
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    db_ok = False
    redis_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        redis_ok = bool(await r.ping())
        await r.aclose()
    except Exception:
        redis_ok = False

    overall = "healthy" if db_ok else "degraded"
    return {
        "status": overall,
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }


@app.get("/")
async def root():
    return {
        "message": f"Bem-vindo ao {settings.PROJECT_NAME} v{settings.VERSION}",
        "ceo": "Jeffrey (CEO & Principal AI Engineer)",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR,
    }
