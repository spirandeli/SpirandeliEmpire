"""Pytest fixtures for SpirandeliEmpire tests"""

import pytest_asyncio
from app.database.session import engine, Base
from app.auth.dependencies import seed_default_owner_if_needed
from app.services.agent_service import agent_service
from app.services.integration_service import integration_service


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_default_owner_if_needed()
    await agent_service.seed_agents_if_needed()
    await integration_service.seed_integrations_if_needed()
    yield
    await engine.dispose()
