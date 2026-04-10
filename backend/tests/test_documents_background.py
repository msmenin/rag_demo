"""Tests for document upload endpoint with background processing."""
import pytest
from pathlib import Path
import io
import tempfile
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


class TestDocumentBackgroundProcessing:
    """Tests for document upload with background processing."""

    @pytest.fixture
    def mock_embedding_model(self):
        """Mock embedding model for tests."""
        from llama_index.core.embeddings import MockEmbedding
        return MockEmbedding(embed_dim=8)

    @pytest.mark.asyncio
    async def test_upload_success(self, async_client: AsyncClient, db_session):
        """Test that upload returns success."""
        # Create workspace
        response = await async_client.post("/workspace/")
        assert response.status_code == 200
        workspace_id = response.json()["id"]
        
        # Upload a minimal valid PDF
        import fitz
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Test content")
            doc.save(f.name)
            doc.close()
            
            with open(f.name, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            Path(f.name).unlink()
        
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        response = await async_client.post(
            f"/workspace/{workspace_id}/documents/",
            files=files
        )
        
        # Verify upload succeeded
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["filename"] == "test.pdf"
        
        # Clean up
        file_path = Path("uploads") / workspace_id / "test.pdf"
        if file_path.exists():
            file_path.unlink()
            file_path.parent.rmdir()

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_status(self, async_client: AsyncClient, db_session, mock_embedding_model):
        """Test that status endpoint returns status."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            # Create workspace
            response = await async_client.post("/workspace/")
            assert response.status_code == 200
            workspace_id = response.json()["id"]
            
            # Upload a minimal valid PDF
            import fitz
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                doc = fitz.open()
                page = doc.new_page()
                page.insert_text((100, 100), "Test")
                doc.save(f.name)
                doc.close()
                
                with open(f.name, 'rb') as pdf_file:
                    pdf_content = pdf_file.read()
                
                Path(f.name).unlink()
            
            files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
            response = await async_client.post(
                f"/workspace/{workspace_id}/documents/",
                files=files
            )
            
            # Allow background task to complete (or fail silently)
            # In production, this would be a real background task
            # For testing, we just verify the endpoint structure
            
            assert response.status_code == 200
            document_id = response.json()["id"]
            
            # Get status - this tests the endpoint exists and returns proper structure
            response = await async_client.get(
                f"/workspace/{workspace_id}/documents/{document_id}/status"
            )
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "status" in data
            assert "page_count" in data
            assert "error_message" in data
            # Status should be one of these values
            assert data["status"] in ["processing", "complete", "error"]
            
            # Clean up
            file_path = Path("uploads") / workspace_id / "test.pdf"
            if file_path.exists():
                file_path.unlink()
                file_path.parent.rmdir()

    @pytest.mark.asyncio
    async def test_delete_endpoint_works(self, async_client: AsyncClient, db_session):
        """Test that delete endpoint works."""
        # Create workspace
        response = await async_client.post("/workspace/")
        assert response.status_code == 200
        workspace_id = response.json()["id"]
        
        # Upload a PDF
        import fitz
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "Test content for deletion")
            doc.save(f.name)
            doc.close()
            
            with open(f.name, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
            
            Path(f.name).unlink()
        
        files = {"file": ("delete_test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        response = await async_client.post(
            f"/workspace/{workspace_id}/documents/",
            files=files
        )
        document_id = response.json()["id"]
        
        # Delete document
        response = await async_client.delete(
            f"/workspace/{workspace_id}/documents/{document_id}"
        )
        
        # Verify delete succeeded
        assert response.status_code == 204
        
        # Verify file deleted
        file_path = Path("uploads") / workspace_id / "delete_test.pdf"
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_status_endpoint_nonexistent_document(self, async_client: AsyncClient, db_session):
        """Test that status endpoint returns 404 for non-existent document."""
        # Create workspace
        response = await async_client.post("/workspace/")
        assert response.status_code == 200
        workspace_id = response.json()["id"]
        
        # Try to get status of non-existent document
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(
            f"/workspace/{workspace_id}/documents/{fake_id}/status"
        )
        
        # Verify 404
        assert response.status_code == 404
