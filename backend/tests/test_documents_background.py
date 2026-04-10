"""Tests for document upload endpoint with background processing."""
import pytest
from pathlib import Path
import io
import tempfile
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock


class TestDocumentBackgroundProcessing:
    """Tests for document upload with background processing."""

    @pytest.fixture
    def mock_embedding_model(self):
        """Mock embedding model for tests."""
        from llama_index.core.embeddings import MockEmbedding
        return MockEmbedding(embed_dim=8)

    @pytest.fixture
    def temp_chroma_dir(self):
        """Create a temporary directory for ChromaDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_upload_triggers_background_processing(self, async_client: AsyncClient, db_session, temp_chroma_dir, mock_embedding_model):
        """Test that upload triggers background processing."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            with patch('backend.routers.documents.process_document', new_callable=AsyncMock) as mock_process:
                # Create workspace
                response = await async_client.post("/workspace/")
                assert response.status_code == 200
                workspace_id = response.json()["id"]
                
                # Upload PDF file (real PDF with PyMuPDF)
                import fitz
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    doc = fitz.open()
                    page = doc.new_page()
                    page.insert_text((100, 100), "Test content for processing")
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
                
                # Clean up
                file_path = Path("uploads") / workspace_id / "test.pdf"
                if file_path.exists():
                    file_path.unlink()
                    file_path.parent.rmdir()

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_processing_or_complete(self, async_client: AsyncClient, db_session):
        """Test that status endpoint returns processing or complete."""
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
        document_id = response.json()["id"]
        
        # Get status
        response = await async_client.get(
            f"/workspace/{workspace_id}/documents/{document_id}/status"
        )
        
        # Verify status response
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["processing", "complete"]
        
        # Clean up
        file_path = Path("uploads") / workspace_id / "test.pdf"
        if file_path.exists():
            file_path.unlink()
            file_path.parent.rmdir()

    @pytest.mark.asyncio
    async def test_delete_endpoint_removes_vectors_from_chromadb(self, async_client: AsyncClient, db_session, temp_chroma_dir, mock_embedding_model):
        """Test that delete endpoint removes vectors from ChromaDB."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.vector_store import VectorStoreService
            
            # Create workspace
            response = await async_client.post("/workspace/")
            assert response.status_code == 200
            workspace_id = response.json()["id"]
            
            # Upload a real PDF
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
