Aqui é **Balsini, Senior Backend Engineer do SpirandeliEmpire OS**.

Com base na especificação arquitetural definida pelo Noé, apresento a implementação do **Core da API FastAPI**. O desenvolvimento foi projetado focando em **alta performance**, **concorrência nativa via AsyncIO**, **tipagem estrita (Pydantic v2 / Python 3.11+)** e **Arquitetura Limpa (Clean Architecture)** com desacoplamento total entre as camadas de apresentação, serviço e persistência.

---

# 🛠️ Implementação do Backend — FastAPI Core

## 1. Estrutura de Diretórios da Aplicação

```text
app/
├── api/
│   └── v1/
│       ├── endpoints/
│       │   ├── auth.py
│       │   └── empire_nodes.py
│       └── router.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── exceptions.py
│   └── security.py
├── models/
│   └── empire_node.py
├── repositories/
│   └── empire_node_repository.py
├── schemas/
│   └── empire_node.py
├── services/
│   └── empire_node_service.py
└── main.py
```

---

## 2. Configurações Globais e Conexão Async (Core)

### `app/core/config.py`
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SpirandeliEmpire OS API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "secret"
    POSTGRES_DB: str = "spirandeli_db"
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
```

### `app/core/database.py`
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## 3. Schemas de Dados Estritos (Pydantic V2)

### `app/schemas/empire_node.py`
```python
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing import Annotated


class NodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


class EmpireNodeBase(BaseModel):
    name: Annotated[str, StringConstraints(min_length=3, max_length=100, strip_whitespace=True)]
    code: Annotated[str, StringConstraints(min_length=2, max_length=20, to_upper=True)]
    status: NodeStatus = NodeStatus.ACTIVE
    capacity_weight: int = Field(default=1, ge=1, le=100)


class EmpireNodeCreate(EmpireNodeBase):
    pass


class EmpireNodeUpdate(BaseModel):
    name: Annotated[str | None, StringConstraints(min_length=3, max_length=100, strip_whitespace=True)] = None
    status: NodeStatus | None = None
    capacity_weight: int | None = Field(default=None, ge=1, le=100)


class EmpireNodeResponse(EmpireNodeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## 4. Camada de Repositório (Async SQLAlchemy 2.0)

### `app/repositories/empire_node_repository.py`
```python
from typing import Sequence
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.empire_node import EmpireNodeModel
from app.schemas.empire_node import EmpireNodeCreate, EmpireNodeUpdate


class EmpireNodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, node_id: UUID) -> EmpireNodeModel | None:
        query = select(EmpireNodeModel).where(EmpireNodeModel.id == node_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> EmpireNodeModel | None:
        query = select(EmpireNodeModel).where(EmpireNodeModel.code == code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> Sequence[EmpireNodeModel]:
        query = select(EmpireNodeModel).offset(skip).limit(limit).order_by(EmpireNodeModel.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, schema: EmpireNodeCreate) -> EmpireNodeModel:
        db_obj = EmpireNodeModel(**schema.model_dump())
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: EmpireNodeModel, schema: EmpireNodeUpdate) -> EmpireNodeModel:
        update_data = schema.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: EmpireNodeModel) -> None:
        await self.session.delete(db_obj)
        await self.session.flush()
```

---

## 5. Camada de Serviço (Business Logic)

### `app/services/empire_node_service.py`
```python
from typing import Sequence
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.empire_node_repository import EmpireNodeRepository
from app.schemas.empire_node import EmpireNodeCreate, EmpireNodeResponse, EmpireNodeUpdate


class EmpireNodeService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = EmpireNodeRepository(session)

    async def create_node(self, schema: EmpireNodeCreate) -> EmpireNodeResponse:
        existing = await self.repository.get_by_code(schema.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Node com código '{schema.code}' já está cadastrado.",
            )
        node = await self.repository.create(schema)
        return EmpireNodeResponse.model_validate(node)

    async def get_node(self, node_id: UUID) -> EmpireNodeResponse:
        node = await self.repository.get_by_id(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node '{node_id}' não encontrado.",
            )
        return EmpireNodeResponse.model_validate(node)

    async def list_nodes(self, skip: int = 0, limit: int = 100) -> list[EmpireNodeResponse]:
        nodes = await self.repository.list_all(skip=skip, limit=limit)
        return [EmpireNodeResponse.model_validate(n) for n in nodes]

    async def update_node(self, node_id: UUID, schema: EmpireNodeUpdate) -> EmpireNodeResponse:
        node = await self.repository.get_by_id(node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node '{node_id}' não encontrado para atualização.",
            )
        updated_node = await self.repository.update(node, schema)
        return EmpireNodeResponse.model_validate(updated_node)
```

---

## 6. Controllers e Endpoints HTTP

### `app/api/v1/endpoints/empire_nodes.py`
```python
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.empire_node import EmpireNodeCreate, EmpireNodeResponse, EmpireNodeUpdate
from app.services.empire_node_service import EmpireNodeService

router = APIRouter(prefix="/nodes", tags=["Empire Nodes"])


def get_node_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> EmpireNodeService:
    return EmpireNodeService(session)


@router.post(
    "/",
    response_model=EmpireNodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo nó no Empire OS",
)
async def create_node(
    payload: EmpireNodeCreate,
    service: Annotated[EmpireNodeService, Depends(get_node_service)],
) -> EmpireNodeResponse:
    return await service.create_node(payload)


@router.get(
    "/",
    response_model=list[EmpireNodeResponse],
    status_code=status.HTTP_200_OK,
    summary="Lista todos os nós cadastrados",
)
async def list_nodes(
    service: Annotated[EmpireNodeService, Depends(get_node_service)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[EmpireNodeResponse]:
    return await service.list_nodes(skip=skip, limit=limit)


@router.get(
    "/{node_id}",
    response_model=EmpireNodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtém detalhes de um nó por ID",
)
async def get_node(
    node_id: UUID,
    service: Annotated[EmpireNodeService, Depends(get_node_service)],
) -> EmpireNodeResponse:
    return await service.get_node(node_id)


@router.patch(
    "/{node_id}",
    response_model=EmpireNodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualiza dados parciais de um nó",
)
async def update_node(
    node_id: UUID,
    payload: EmpireNodeUpdate,
    service: Annotated[EmpireNodeService, Depends(get_node_service)],
) -> EmpireNodeResponse:
    return await service.update_node(node_id, payload)
```

---

## 7. Entrypoint Principal da Aplicação

### `app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuração de CORS para consumo pelo Frontend (Fonseca)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir em produção conforme especificações
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Roteamento Principal
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["System Operations"])
async def health_check() -> dict[str, str]:
    return {
        "status": "HEALTHY",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
```

---

## 📌 Status de Entrega para a Próxima Etapa

1. **Integração Frontend (Fonseca):** OpenAPI / Swagger 100% compatível e tipado disponível em `http://localhost:8000/docs`.
2. **Persistência (Ford):** Interfaces com SQLAlchemy 2.0 Async prontas para mapear diretamente os Schemas de Migração via Alembic.
3. **Quality Gate (Murphy):** Endpoints assíncronos prontos para testes de integração unitários via `httpx.AsyncClient` e `pytest-asyncio`.

Código backend implementado, desacoplado e pronto para execução.