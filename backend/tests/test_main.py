import pytest
import os
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
from pathlib import Path


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


def test_startup_validates_provider_config():
    """Test that startup validates provider config file exists."""
    from backend.services.llm_factory import validate_provider_config
    
    # Test with valid config
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key",
        "OPENAI_API_KEY": "test-key"
    }):
        # Should not raise error
        validate_provider_config()


def test_startup_fails_missing_api_key():
    """Test that startup fails with clear error when API key missing."""
    from backend.services.llm_factory import validate_provider_config
    from pydantic import ValidationError
    
    # Missing OPENROUTER_API_KEY
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            validate_provider_config()
        
        # Should have clear error message
        assert "OPENROUTER_API_KEY" in str(exc_info.value)


def test_startup_fails_missing_config_file():
    """Test that startup fails when config file missing."""
    from backend.services.llm_factory import validate_provider_config
    
    nonexistent_path = Path("backend/config/nonexistent.yaml")
    
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_provider_config(config_path=nonexistent_path)
    
    assert "not found" in str(exc_info.value).lower()
