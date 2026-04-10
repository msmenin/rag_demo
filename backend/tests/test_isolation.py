"""Tests for workspace isolation guarantees."""
import pytest
import io
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workspace_isolation_list(async_client: AsyncClient, db_session):
    """Test that Workspace A cannot list Workspace B's documents."""
    # Create workspace A
    response = await async_client.post("/workspace/")
    workspace_a_id = response.json()["id"]
    
    # Create workspace B
    response = await async_client.post("/workspace/")
    workspace_b_id = response.json()["id"]
    
    # Upload document to workspace A
    pdf_content = b"%PDF-1.4 test content"
    files = {"file": ("workspace_a_doc.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = await async_client.post(
        f"/workspace/{workspace_a_id}/documents/",
        files=files
    )
    assert response.status_code == 200
    
    # List documents in workspace B (should be empty)
    response = await async_client.get(f"/workspace/{workspace_b_id}/documents/")
    assert response.status_code == 200
    documents = response.json()
    assert len(documents) == 0, "Workspace B should not see Workspace A's documents"


@pytest.mark.asyncio
async def test_workspace_isolation_access(async_client: AsyncClient, db_session):
    """Test that Workspace A cannot access/delete Workspace B's document by ID."""
    # Create workspace A with document X
    response = await async_client.post("/workspace/")
    workspace_a_id = response.json()["id"]
    
    pdf_content = b"%PDF-1.4 test content"
    files = {"file": ("document_x.pdf", io.BytesIO(pdf_content), "application/pdf")}
    response = await async_client.post(
        f"/workspace/{workspace_a_id}/documents/",
        files=files
    )
    document_x_id = response.json()["id"]
    
    # Create workspace B
    response = await async_client.post("/workspace/")
    workspace_b_id = response.json()["id"]
    
    # Try to delete document X from workspace B (should fail with 404)
    response = await async_client.delete(
        f"/workspace/{workspace_b_id}/documents/{document_x_id}"
    )
    assert response.status_code == 404, "Workspace B cannot delete Workspace A's document"


@pytest.mark.asyncio
async def test_workspace_isolation_cross_workspace(async_client: AsyncClient, db_session):
    """Test complete isolation between two workspaces with multiple documents."""
    # Create workspace A with 3 documents
    response = await async_client.post("/workspace/")
    workspace_a_id = response.json()["id"]
    
    for i in range(3):
        pdf_content = b"%PDF-1.4 test content"
        files = {"file": (f"workspace_a_{i}.pdf", io.BytesIO(pdf_content), "application/pdf")}
        await async_client.post(
            f"/workspace/{workspace_a_id}/documents/",
            files=files
        )
    
    # Create workspace B with 2 documents
    response = await async_client.post("/workspace/")
    workspace_b_id = response.json()["id"]
    
    for i in range(2):
        pdf_content = b"%PDF-1.4 test content"
        files = {"file": (f"workspace_b_{i}.pdf", io.BytesIO(pdf_content), "application/pdf")}
        await async_client.post(
            f"/workspace/{workspace_b_id}/documents/",
            files=files
        )
    
    # List documents in workspace A (should have 3)
    response = await async_client.get(f"/workspace/{workspace_a_id}/documents/")
    workspace_a_docs = response.json()
    assert len(workspace_a_docs) == 3
    assert all(doc["workspace_id"] == workspace_a_id for doc in workspace_a_docs)
    
    # List documents in workspace B (should have 2)
    response = await async_client.get(f"/workspace/{workspace_b_id}/documents/")
    workspace_b_docs = response.json()
    assert len(workspace_b_docs) == 2
    assert all(doc["workspace_id"] == workspace_b_id for doc in workspace_b_docs)
    
    # Verify no overlap in document IDs
    a_ids = {doc["id"] for doc in workspace_a_docs}
    b_ids = {doc["id"] for doc in workspace_b_docs}
    assert len(a_ids & b_ids) == 0, "Workspaces should have no overlapping documents"


@pytest.mark.asyncio
async def test_workspace_deletion_cascade(async_client: AsyncClient, db_session):
    """Test that deleting a workspace cascades to its documents."""
    from pathlib import Path
    
    # Create workspace with documents
    response = await async_client.post("/workspace/")
    workspace_id = response.json()["id"]
    
    # Upload 5 documents
    for i in range(5):
        pdf_content = b"%PDF-1.4 test content"
        files = {"file": (f"cascade_{i}.pdf", io.BytesIO(pdf_content), "application/pdf")}
        await async_client.post(
            f"/workspace/{workspace_id}/documents/",
            files=files
        )
    
    # Verify documents exist
    response = await async_client.get(f"/workspace/{workspace_id}/documents/")
    assert len(response.json()) == 5
    
    # Note: We don't test workspace deletion here because the API doesn't have
    # a DELETE /workspace/{id} endpoint yet. The cascade delete is tested at the
    # model level in test_document_model.py


@pytest.mark.asyncio
async def test_full_integration_flow(async_client: AsyncClient, db_session):
    """Integration test: create workspace, upload documents, list, delete, verify."""
    from pathlib import Path
    
    # Create workspace
    response = await async_client.post("/workspace/")
    workspace_id = response.json()["id"]
    
    # Upload 3 documents
    doc_ids = []
    for i in range(3):
        pdf_content = b"%PDF-1.4 test content"
        files = {"file": (f"integration_{i}.pdf", io.BytesIO(pdf_content), "application/pdf")}
        response = await async_client.post(
            f"/workspace/{workspace_id}/documents/",
            files=files
        )
        assert response.status_code == 200
        doc_ids.append(response.json()["id"])
    
    # List documents (verify 3)
    response = await async_client.get(f"/workspace/{workspace_id}/documents/")
    documents = response.json()
    assert len(documents) == 3
    
    # Delete 1 document
    response = await async_client.delete(
        f"/workspace/{workspace_id}/documents/{doc_ids[0]}"
    )
    assert response.status_code == 204
    
    # List documents (verify 2)
    response = await async_client.get(f"/workspace/{workspace_id}/documents/")
    documents = response.json()
    assert len(documents) == 2
    assert doc_ids[0] not in {doc["id"] for doc in documents}
    
    # Verify file count on disk matches database
    upload_dir = Path("uploads") / workspace_id
    assert upload_dir.exists()
    file_count = len(list(upload_dir.glob("*.pdf")))
    assert file_count == 2, f"Expected 2 files on disk, found {file_count}"
    
    # Clean up
    for file in upload_dir.glob("*.pdf"):
        file.unlink()
    upload_dir.rmdir()
