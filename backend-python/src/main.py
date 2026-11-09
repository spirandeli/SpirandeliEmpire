from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from src.config import get_settings
from src.services.media.media_settings import STORAGE_MEDIA_DIR, STORAGE_OUTPUT_DIR
from src.routers import (
    admin,
    agent,
    approvals,
    auth,
    businesses,
    calendar,
    integrations,
    languages,
    media,
    storage_viewer,
    tasks,
    webhooks,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-criação de tabelas que ainda não existem
    try:
        from src.database import engine, Base
        from sqlalchemy import text
        import src.models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                col_res = await conn.execute(text("SHOW COLUMNS FROM tasks LIKE 'status_log'"))
                if not col_res.scalar():
                    await conn.execute(text("ALTER TABLE tasks ADD COLUMN status_log TEXT NULL"))
            except Exception:
                pass
    except Exception as e:
        print(f"Warning initializing database tables: {e}")

    # Auto-indexação da base de conhecimento RAG caso vazia
    try:
        from src.services.knowledge_service import get_knowledge_stats, index_all_knowledge
        stats = get_knowledge_stats()
        if stats.get("indexed_chunks", 0) == 0:
            await index_all_knowledge(force=False)
    except Exception:
        pass
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="ABVOS - Autonomous Business Venture OS (FastAPI Backend)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors_dict = {}
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err["loc"] if loc != "body")
        msg = err["msg"]
        if field not in errors_dict:
            errors_dict[field] = []
        errors_dict[field].append(msg)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Os dados fornecidos são inválidos.",
            "errors": errors_dict,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        content = dict(exc.detail)
        if "message" not in content:
            if "errors" in content:
                first_err = next(iter(content["errors"].values()), None)
                if isinstance(first_err, list) and first_err:
                    content["message"] = first_err[0]
                elif isinstance(first_err, str):
                    content["message"] = first_err
                else:
                    content["message"] = "Os dados fornecidos são inválidos."
            else:
                content["message"] = "Erro ao processar requisição."
        return JSONResponse(status_code=exc.status_code, content=content)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail), "detail": str(exc.detail)},
    )


# Middleware para normalizar prefixos duplicados (/api/api/... -> /api/...)
@app.middleware("http")
async def normalize_duplicate_api_prefix(request: Request, call_next):
    path = request.scope.get("path", "")
    while path.startswith("/api/api/"):
        path = "/api/" + path[len("/api/api/"):]
        request.scope["path"] = path
    return await call_next(request)


# Health check
@app.api_route("/up", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}


# Rotas da API sob o prefixo /api
app.include_router(auth.router, prefix="/api")
app.include_router(businesses.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(languages.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(media.router, prefix="/api")
app.include_router(storage_viewer.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")

# Rotas compatíveis sob o prefixo /api/v1
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(media.router, prefix="/api/v1")
app.include_router(storage_viewer.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")

# Rota estática direta para inspeção/download de mídia e outputs do pipeline
STORAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(STORAGE_OUTPUT_DIR)), name="outputs")

STORAGE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(STORAGE_MEDIA_DIR)), name="media-static")
