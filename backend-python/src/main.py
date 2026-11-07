from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
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
    tasks,
    webhooks,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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


# Health check
@app.get("/up")
@app.get("/api/health")
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
app.include_router(webhooks.router, prefix="/api")
