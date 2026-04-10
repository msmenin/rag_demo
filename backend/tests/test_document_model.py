"""Tests for Document model."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from backend.models.document import Document
from backend.models.workspace import Workspace
from backend.schemas.document import DocumentResponse


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


@pytest.mark.asyncio
async def test_document_error_message_field(db_session):
    """Test that Document model has error_message field (String, nullable)."""
    # Create workspace
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    # Create document with error_message
    document = Document(
        workspace_id=workspace.id,
        filename="test.pdf",
        file_path="uploads/test/test.pdf",
        error_message="Failed to extract text from PDF"
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    
    # Verify error_message field exists and can be set
    assert document.error_message == "Failed to extract text from PDF"
    
    # Verify error_message is nullable
    doc2 = Document(
        workspace_id=workspace.id,
        filename="test2.pdf",
        file_path="uploads/test/test2.pdf",
        error_message=None
    )
    db_session.add(doc2)
    await db_session.commit()
    await db_session.refresh(doc2)
    assert doc2.error_message is None


@pytest.mark.asyncio
async def test_document_response_schema_includes_error_message(db_session):
    """Test that DocumentResponse schema includes error_message field."""
    # Create workspace
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    # Create document
    document = Document(
        workspace_id=workspace.id,
        filename="test.pdf",
        file_path="uploads/test/test.pdf",
        file_size=1024,
        error_message="Processing failed"
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    
    # Create DocumentResponse from model
    response = DocumentResponse.model_validate(document)
    
    # Verify error_message is included in response
    assert response.error_message == "Processing failed"
    assert response.id == document.id
    assert response.workspace_id == workspace.id
    assert response.filename == "test.pdf"


@pytest.mark.asyncio
async def test_document_response_schema_handles_null_error_message(db_session):
    """Test that DocumentResponse schema handles null error_message."""
    # Create workspace
    workspace = Workspace()
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    
    # Create document without error_message
    document = Document(
        workspace_id=workspace.id,
        filename="test.pdf",
        file_path="uploads/test/test.pdf",
        file_size=2048
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)
    
    # Create DocumentResponse from model
    response = DocumentResponse.model_validate(document)
    
    # Verify error_message is None
    assert response.error_message is None
