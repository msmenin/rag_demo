import pytest
from httpx import AsyncClient
from uuid import UUID
from backend.tests.conftest import *


@pytest.mark.asyncio
async def test_create_workspace(async_client: AsyncClient):
    """Test 1: POST /workspace/ creates workspace and returns 200 with {id, created_at}"""
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "created_at" in data
    # Verify UUID format
    UUID(data["id"])  # Will raise ValueError if invalid


@pytest.mark.asyncio
async def test_get_workspace(async_client: AsyncClient):
    """Test 2: GET /workspace/{id} returns workspace info for valid ID"""
    # Create a workspace first
    create_response = await async_client.post("/workspace/")
    workspace_id = create_response.json()["id"]
    
    # Get the workspace
    get_response = await async_client.get(f"/workspace/{workspace_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == workspace_id
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_nonexistent_workspace(async_client: AsyncClient):
    """Test 3: GET /workspace/{nonexistent_id} returns 404"""
    # Use a valid UUID that doesn't exist
    nonexistent_id = str(UUID("00000000-0000-0000-0000-000000000000"))
    response = await async_client.get(f"/workspace/{nonexistent_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_invalid_workspace_id(async_client: AsyncClient):
    """Test 4: GET /workspace/{invalid_uuid} returns 400"""
    response = await async_client.get("/workspace/invalid-id")
    assert response.status_code == 400