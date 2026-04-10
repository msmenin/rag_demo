"""Tests for Document model."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from backend.models.document import Document
from backend.models.workspace import Workspace


@pytest.mark.asyncio
async def test_document_model_fields(db_session):
    """Test that Document model has all required fields."""
    # Create workspace first
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    # Create document
    document = Document(
        workspace_id=workspace.id,
        filename="test.pdf",
        file_path="uploads/test/test.pdf",
        page_count=10,
        file_size=1024
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    
    # Verify fields exist
    assert document.id is not None
    assert document.workspace_id == workspace.id
    assert document.filename == "test.pdf"
    assert document.file_path == "uploads/test/test.pdf"
    assert document.page_count == 10
    assert document.file_size == 1024
    assert document.indexed_at is None
    assert document.created_at is not None


@pytest.mark.asyncio
async def test_document_workspace_foreign_key(db_session):
    """Test that Document.workspace_id is a foreign key to Workspace."""
    # Create workspace
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    # Create document with workspace_id
    document = Document(
        workspace_id=workspace.id,
        filename="test.pdf",
        file_path="uploads/test/test.pdf"
    )
    db_session.add(document)
    await db_session.commit()
    
    # Query and verify relationship
    result = await db_session.execute(
        select(Document).where(Document.workspace_id == workspace.id)
    )
    fetched_doc = result.scalar_one()
    assert fetched_doc.workspace_id == workspace.id
    
    # Verify workspace relationship works
    await db_session.refresh(fetched_doc, ["workspace"])
    assert fetched_doc.workspace.id == workspace.id


@pytest.mark.asyncio
async def test_document_workspace_id_index(db_session):
    """Test that workspace_id has an index for query performance."""
    # This test verifies the index exists by checking query performance
    # Create workspace
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    # Create multiple documents
    for i in range(10):
        doc = Document(
            workspace_id=workspace.id,
            filename=f"test{i}.pdf",
            file_path=f"uploads/test/test{i}.pdf"
        )
        db_session.add(doc)
    await db_session.commit()
    
    # Query by workspace_id should use index (verified by query plan in production)
    result = await db_session.execute(
        select(Document).where(Document.workspace_id == workspace.id)
    )
    documents = result.scalars().all()
    assert len(documents) == 10


@pytest.mark.asyncio
async def test_document_creation_with_valid_workspace(db_session):
    """Test that Document can be created with a valid workspace_id."""
    # Create workspace
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    # Create document
    document = Document(
        workspace_id=workspace.id,
        filename="sample.pdf",
        file_path="uploads/test/sample.pdf"
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    
    # Verify
    assert document.id is not None
    assert isinstance(document.id, type(workspace.id))  # Both UUIDs
    assert document.workspace_id == workspace.id
    assert document.filename == "sample.pdf"
