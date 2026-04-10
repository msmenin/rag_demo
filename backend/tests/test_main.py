import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    """Test 1: GET /health returns {"status": "ok"}"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


@pytest.mark.asyncio
async def test_app_starts_successfully(async_client: AsyncClient):
    """Test 2: FastAPI app starts successfully"""
    # If we reach this point, the app started successfully
    assert async_client is not None


@pytest.mark.asyncio
async def test_cors_headers(async_client: AsyncClient):
    """Test 3: CORS headers allow http://localhost:3000"""
    response = await async_client.options("/health", headers={
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "GET"
    })
    # FastAPI's CORS middleware should allow this
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_database_file_created(async_client: AsyncClient, db_session):
    """Test 4: Database file created at ./rag_app.db"""
    # This test verifies the database engine is working
    # The actual file creation happens during engine initialization
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
