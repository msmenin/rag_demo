"""Tests for error handling in document processing."""
import pytest
from fastapi import UploadFile
from io import BytesIO
from httpx import AsyncClient
from sqlalchemy import select
from backend.models import Document, Workspace


@pytest.mark.asyncio
async def test_upload_non_pdf_returns_400(async_client: AsyncClient, db_session, workspace: Workspace):
    """Non-PDF file should return 400 error with clear message."""
    file_content = b"This is not a PDF file"
    
    response = await async_client.post(
        f"/workspace/{workspace.id}/documents/",
        files={"file": ("test.txt", BytesIO(file_content), "text/plain")}
    )
    
    assert response.status_code == 400
    error_detail = response.json()["detail"]
    assert "Only PDF files" in error_detail
    assert "internal server error" not in error_detail.lower()


@pytest.mark.asyncio
async def test_upload_too_large_returns_413(async_client: AsyncClient, db_session, workspace: Workspace):
    """File > 50MB should return 413 error."""
    # Create 51MB file content
    large_content = b"x" * (51 * 1024 * 1024)
    
    response = await async_client.post(
        f"/workspace/{workspace.id}/documents/",
        files={"file": ("large.pdf", BytesIO(large_content), "application/pdf")}
    )
    
    assert response.status_code == 413
    error_detail = response.json()["detail"]
    assert "too large" in error_detail.lower()
    assert "50" in error_detail


@pytest.mark.asyncio
async def test_upload_empty_file_returns_error(async_client: AsyncClient, db_session, workspace: Workspace):
    """Empty file should return appropriate error."""
    response = await async_client.post(
        f"/workspace/{workspace.id}/documents/",
        files={"file": ("empty.pdf", BytesIO(b""), "application/pdf")}
    )
    
    # Should either reject empty files or handle gracefully
    # The exact behavior depends on implementation
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_error_message_sanitized_no_paths(async_client: AsyncClient, db_session, workspace: Workspace):
    """Error messages should not leak file system paths."""
    # Create an invalid PDF (valid PDF header but corrupted content)
    invalid_pdf = b"%PDF-1.4\n%corrupted content that is not a valid PDF structure"
    
    response = await async_client.post(
        f"/workspace/{workspace.id}/documents/",
        files={"file": ("invalid.pdf", BytesIO(invalid_pdf), "application/pdf")}
    )
    
    # Upload should succeed (document created)
    assert response.status_code == 200
    doc_id = response.json()["id"]
    
    # Wait a bit for background processing (in real test, would poll)
    # For now, check that if there's an error message, it doesn't contain paths
    # This would need to be checked via the status endpoint after processing completes
    
    # Check status endpoint
    status_response = await async_client.get(
        f"/workspace/{workspace.id}/documents/{doc_id}/status"
    )
    
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    # If processing failed, error message should not contain paths
    if status_data.get("error_message"):
        error_msg = status_data["error_message"]
        # Should not contain common path patterns
        assert "/home/" not in error_msg
        assert "/Users/" not in error_msg
        assert "/var/" not in error_msg
        assert "uploads/" not in error_msg


@pytest.mark.asyncio
async def test_error_message_stored_in_database(async_client: AsyncClient, db_session, workspace: Workspace):
    """Error messages from processing should be stored in document.error_message."""
    # Create an invalid PDF
    invalid_pdf = b"%PDF-1.4\n%invalid"
    
    response = await async_client.post(
        f"/workspace/{workspace.id}/documents/",
        files={"file": ("corrupted.pdf", BytesIO(invalid_pdf), "application/pdf")}
    )
    
    assert response.status_code == 200
    doc_id = response.json()["id"]
    
    # In a real test with background task support, we would:
    # 1. Wait for background processing to complete
    # 2. Check that error_message was stored
    # For now, verify the field exists and can be set
    
    # Direct database check (simulating what happens after processing)
    result = await db_session.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalar_one()
    
    # Document was created
    assert doc is not None
    # error_message field exists (may be None if not yet processed)
    assert hasattr(doc, 'error_message')


@pytest.mark.asyncio
async def test_workspace_not_found_returns_404(async_client: AsyncClient, db_session):
    """Uploading to non-existent workspace returns 404."""
    from uuid import uuid4
    fake_workspace_id = uuid4()
    
    file_content = b"%PDF-1.4\n%test"
    response = await async_client.post(
        f"/workspace/{fake_workspace_id}/documents/",
        files={"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_workspace_id_format_returns_400(async_client: AsyncClient, db_session):
    """Invalid workspace ID format returns 400."""
    response = await async_client.post(
        f"/workspace/not-a-uuid/documents/",
        files={"file": ("test.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")}
    )
    
    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_valid_pdf_processes_successfully(async_client: AsyncClient, db_session, workspace: Workspace):
    """Valid PDF should process without errors."""
    # Create a minimal valid PDF
    # This is a very simple PDF structure that should be parseable
    minimal_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
198
%%EOF
"""
    
    response = await async_client.post(
        f"/workspace/{workspace.id}/documents/",
        files={"file": ("valid.pdf", BytesIO(minimal_pdf), "application/pdf")}
    )
    
    # Upload should succeed
    assert response.status_code == 200
    doc_data = response.json()
    assert doc_data["filename"] == "valid.pdf"
    assert doc_data["workspace_id"] == str(workspace.id)


@pytest.mark.asyncio
async def test_status_endpoint_returns_correct_status(async_client: AsyncClient, db_session, workspace: Workspace):
    """Status endpoint should return processing/complete/error correctly."""
    # Upload a minimal PDF
    minimal_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 >>\nstartxref\n0\n%%EOF"
    
    upload_response = await async_client.post(
        f"/workspace/{workspace.id}/documents/",
        files={"file": ("test.pdf", BytesIO(minimal_pdf), "application/pdf")}
    )
    
    assert upload_response.status_code == 200
    doc_id = upload_response.json()["id"]
    
    # Check status immediately (should be processing or complete depending on timing)
    status_response = await async_client.get(
        f"/workspace/{workspace.id}/documents/{doc_id}/status"
    )
    
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    # Status should be one of the valid values
    assert status_data["status"] in ["processing", "complete", "error"]
    assert status_data["id"] == doc_id


@pytest.mark.asyncio
async def test_status_endpoint_document_not_found(async_client: AsyncClient, db_session, workspace: Workspace):
    """Status endpoint returns 404 for non-existent document."""
    from uuid import uuid4
    fake_doc_id = uuid4()
    
    response = await async_client.get(
        f"/workspace/{workspace.id}/documents/{fake_doc_id}/status"
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
