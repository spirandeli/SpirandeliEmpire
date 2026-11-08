from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.config import get_settings
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
    tasks,
    webhooks,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-criação de tabelas que ainda não existem
    try:
        from src.database import engine, Base
        import src.models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
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
app.include_router(webhooks.router, prefix="/api")
