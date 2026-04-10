"""Tests for Document API endpoints."""
import pytest
from pathlib import Path
import io
from httpx import AsyncClient
from backend.models import Workspace


@pytest.mark.asyncio
async def test_upload_document_success(async_client: AsyncClient, db_session):
    """Test successful PDF document upload."""
    # Create workspace
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    # Upload PDF file
    pdf_content = b"%PDF-1.4 fake pdf content"
    files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = await async_client.post(
        f"/workspace/{workspace_id}/documents/",
        files=files
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["workspace_id"] == workspace_id
    assert data["filename"] == "test.pdf"
    assert data["file_size"] == len(pdf_content)
    
    # Verify file was created
    file_path = Path("uploads") / workspace_id / "test.pdf"
    assert file_path.exists()
    
    # Clean up
    if file_path.exists():
        file_path.unlink()
        file_path.parent.rmdir()


@pytest.mark.asyncio
async def test_upload_non_pdf(async_client: AsyncClient, db_session):
    """Test that non-PDF files are rejected."""
    # Create workspace
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    # Try to upload text file
    files = {"file": ("test.txt", io.BytesIO(b"text content"), "text/plain")}
    response = await async_client.post(
        f"/workspace/{workspace_id}/documents/",
        files=files
    )
    
    # Verify rejection
    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_path_traversal(async_client: AsyncClient, db_session):
    """Test that path traversal attacks are blocked."""
    # Create workspace
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    # Try to upload with path traversal filename
    pdf_content = b"%PDF-1.4 fake pdf content"
    files = {"file": ("../../../etc/passwd.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = await async_client.post(
        f"/workspace/{workspace_id}/documents/",
        files=files
    )
    
    # Verify upload succeeded (filename should be sanitized)
    assert response.status_code == 200
    data = response.json()
    # Filename should be just the base name, not the full path
    assert data["filename"] == "passwd.pdf"
    
    # Verify file was created in correct location (not in /etc)
    file_path = Path("uploads") / workspace_id / "passwd.pdf"
    assert file_path.exists()
    
    # Clean up
    if file_path.exists():
        file_path.unlink()
        file_path.parent.rmdir()


@pytest.mark.asyncio
async def test_upload_to_nonexistent_workspace(async_client: AsyncClient, db_session):
    """Test that uploading to non-existent workspace returns 404."""
    # Try to upload to fake workspace ID
    fake_id = "00000000-0000-0000-0000-000000000000"
    pdf_content = b"%PDF-1.4 fake pdf content"
    files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = await async_client.post(
        f"/workspace/{fake_id}/documents/",
        files=files
    )
    
    # Verify 404
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_file_size_and_filename_stored(async_client: AsyncClient, db_session):
    """Test that file size and filename are stored in database."""
    # Create workspace
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    # Upload PDF
    pdf_content = b"%PDF-1.4 " + b"x" * 1000  # Create larger content
    files = {"file": ("report.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = await async_client.post(
        f"/workspace/{workspace_id}/documents/",
        files=files
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "report.pdf"
    assert data["file_size"] == len(pdf_content)
    
    # Clean up
    file_path = Path("uploads") / workspace_id / "report.pdf"
    if file_path.exists():
        file_path.unlink()
        file_path.parent.rmdir()


@pytest.mark.asyncio
async def test_list_documents(async_client: AsyncClient, db_session):
    """Test listing documents in a workspace."""
    # Create workspace
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    # Upload multiple documents
    for i in range(3):
        pdf_content = b"%PDF-1.4 test content"
        files = {"file": (f"doc{i}.pdf", io.BytesIO(pdf_content), "application/pdf")}
        await async_client.post(
            f"/workspace/{workspace_id}/documents/",
            files=files
        )
    
    # List documents
    response = await async_client.get(f"/workspace/{workspace_id}/documents/")
    
    # Verify response
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) == 3
    assert all(doc["workspace_id"] == workspace_id for doc in documents)
    
    # Clean up
    for i in range(3):
        file_path = Path("uploads") / workspace_id / f"doc{i}.pdf"
        if file_path.exists():
            file_path.unlink()
    (Path("uploads") / workspace_id).rmdir()


@pytest.mark.asyncio
async def test_delete_document(async_client: AsyncClient, db_session):
    """Test deleting a document."""
    # Create workspace and upload document
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    pdf_content = b"%PDF-1.4 test content"
    files = {"file": ("delete_me.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = await async_client.post(
        f"/workspace/{workspace_id}/documents/",
        files=files
    )
    document_id = response.json()["id"]
    
    # Delete document
    response = await async_client.delete(f"/workspace/{workspace_id}/documents/{document_id}")
    assert response.status_code == 204
    
    # Verify file deleted from disk
    file_path = Path("uploads") / workspace_id / "delete_me.pdf"
    assert not file_path.exists()
    
    # Verify document deleted from database
    response = await async_client.get(f"/workspace/{workspace_id}/documents/")
    documents = response.json()
    assert len(documents) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_document(async_client: AsyncClient, db_session):
    """Test deleting a non-existent document returns 404."""
    # Create workspace
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    # Try to delete non-existent document
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await async_client.delete(f"/workspace/{workspace_id}/documents/{fake_id}")
    
    # Verify 404
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_empty_workspace(async_client: AsyncClient, db_session):
    """Test listing documents in an empty workspace."""
    # Create workspace
    response = await async_client.post("/workspace/")
    assert response.status_code == 200
    workspace_id = response.json()["id"]
    
    # List documents (should be empty)
    response = await async_client.get(f"/workspace/{workspace_id}/documents/")
    
    # Verify empty list
    assert response.status_code == 200
    assert response.json() == []
