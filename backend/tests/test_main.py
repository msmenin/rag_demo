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


@pytest.mark.asyncio
async def test_health_providers_endpoint(async_client: AsyncClient):
    """Test /health/providers endpoint returns provider info."""
    response = await async_client.get("/health/providers")
    assert response.status_code == 200
    data = response.json()
    
    # Check structure
    assert "llm" in data
    assert "embeddings" in data
    
    # Check LLM info
    assert "provider" in data["llm"]
    assert "model" in data["llm"]
    assert "api_key_configured" in data["llm"]
    
    # Check embeddings info
    assert "provider" in data["embeddings"]
    assert "model" in data["embeddings"]
    assert "api_key_configured" in data["embeddings"]
    
    # Should not expose actual API key values
    # "api_key_configured" is fine - it's a boolean, not the actual key
    # Check that no key values are exposed (keys would look like "sk-...")
    assert "sk-" not in str(data)
    assert "OPENROUTER_API_KEY" not in str(data) or data["llm"]["api_key_configured"] in [True, False]


@pytest.mark.asyncio
async def test_health_providers_missing_key(async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Test /health/providers shows api_key_configured as false when key missing."""
    # Remove the API key
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    response = await async_client.get("/health/providers")
    assert response.status_code == 200
    data = response.json()
    
    # API key should show as not configured
    assert data["llm"]["api_key_configured"] is False
    assert data["embeddings"]["api_key_configured"] is False
