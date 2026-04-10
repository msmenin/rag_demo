import pytest
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import select
from backend.database import Base
from backend.models.workspace import Workspace


def test_workspace_model_has_required_fields():
    """Test 1: Workspace model has id, created_at fields"""
    workspace = Workspace()
    assert hasattr(workspace, 'id')
    assert hasattr(workspace, 'created_at')
    assert hasattr(workspace, 'name')


@pytest.mark.asyncio
async def test_workspace_id_defaults_to_uuid_v4(db_session):
    """Test 2: Workspace.id defaults to UUID v4 after persistence"""
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    assert workspace.id is not None
    assert isinstance(workspace.id, UUID)
    # UUID v4 has version 4 in the version field
    assert workspace.id.version == 4


@pytest.mark.asyncio
async def test_workspace_created_at_defaults_to_utcnow(db_session):
    """Test 3: Workspace.created_at defaults to datetime after persistence"""
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    assert workspace.created_at is not None
    assert isinstance(workspace.created_at, datetime)


@pytest.mark.asyncio
async def test_create_workspace_in_database(db_session):
    """Test 4: Can create workspace in database"""
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    assert workspace.id is not None
    assert isinstance(workspace.id, UUID)
    assert workspace.created_at is not None
    
    # Verify it's actually in the database
    result = await db_session.execute(
        select(Workspace).where(Workspace.id == workspace.id)
    )
    found = result.scalar_one()
    assert found.id == workspace.id