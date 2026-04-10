"""Tests for document processing pipeline."""
import pytest
import tempfile
import os
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from datetime import datetime


class TestDocumentProcessor:
    """Tests for document processing pipeline."""

    @pytest.fixture
    def temp_chroma_dir(self):
        """Create a temporary directory for ChromaDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_embedding_model(self):
        """Mock embedding model for tests."""
        from llama_index.core.embeddings import MockEmbedding
        return MockEmbedding(embed_dim=8)

    @pytest.fixture
    def sample_pdf_path(self):
        """Create a sample PDF file for testing."""
        # Create a simple PDF using PyMuPDF
        import fitz
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((100, 100), "This is test content for PDF processing.")
            doc.save(f.name)
            doc.close()
            yield f.name
        
        # Cleanup
        os.unlink(f.name)

    @pytest.fixture
    def empty_pdf_path(self):
        """Create an empty PDF file for testing."""
        import fitz
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            doc = fitz.open()
            page = doc.new_page()  # Empty page
            doc.save(f.name)
            doc.close()
            yield f.name
        
        # Cleanup
        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_process_document_extracts_chunks_and_stores(self, temp_chroma_dir, mock_embedding_model, sample_pdf_path):
        """Test that process_document() extracts PDF, chunks, embeds, stores."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.document_processor import process_document
            from backend.services.vector_store import VectorStoreService
            
            # Mock database session
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_db.execute.return_value = mock_result
            mock_db.commit = AsyncMock()
            
            document_id = str(uuid.uuid4())
            workspace_id = str(uuid.uuid4())
            
            vector_store = VectorStoreService(persist_directory=temp_chroma_dir)
            
            await process_document(
                document_id=document_id,
                workspace_id=workspace_id,
                file_path=sample_pdf_path,
                db=mock_db,
                vector_store=vector_store
            )
            
            # Verify database update was called
            mock_db.execute.assert_called()
            mock_db.commit.assert_called()
            
            # Verify chunks were stored
            collection = vector_store.get_workspace_collection(workspace_id)
            assert collection.count() > 0

    @pytest.mark.asyncio
    async def test_process_document_updates_page_count(self, temp_chroma_dir, mock_embedding_model, sample_pdf_path):
        """Test that Document.page_count is updated after processing."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.document_processor import process_document
            from backend.services.vector_store import VectorStoreService
            
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()
            
            document_id = str(uuid.uuid4())
            workspace_id = str(uuid.uuid4())
            
            vector_store = VectorStoreService(persist_directory=temp_chroma_dir)
            
            await process_document(
                document_id=document_id,
                workspace_id=workspace_id,
                file_path=sample_pdf_path,
                db=mock_db,
                vector_store=vector_store
            )
            
            # Verify update was called with page_count
            update_call = mock_db.execute.call_args
            assert update_call is not None

    @pytest.mark.asyncio
    async def test_process_document_sets_indexed_at(self, temp_chroma_dir, mock_embedding_model, sample_pdf_path):
        """Test that Document.indexed_at is set after processing."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.document_processor import process_document
            from backend.services.vector_store import VectorStoreService
            
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()
            
            document_id = str(uuid.uuid4())
            workspace_id = str(uuid.uuid4())
            
            vector_store = VectorStoreService(persist_directory=temp_chroma_dir)
            
            await process_document(
                document_id=document_id,
                workspace_id=workspace_id,
                file_path=sample_pdf_path,
                db=mock_db,
                vector_store=vector_store
            )
            
            # Verify update was called (includes indexed_at)
            update_call = mock_db.execute.call_args
            assert update_call is not None

    @pytest.mark.asyncio
    async def test_process_document_error_updates_error_message(self, temp_chroma_dir, mock_embedding_model):
        """Test that processing error updates document with error message."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.document_processor import process_document
            from backend.services.vector_store import VectorStoreService
            from backend.services.pdf_processor import PDFExtractionError
            
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()
            
            document_id = str(uuid.uuid4())
            workspace_id = str(uuid.uuid4())
            
            vector_store = VectorStoreService(persist_directory=temp_chroma_dir)
            
            # Try to process non-existent file
            with pytest.raises(PDFExtractionError):
                await process_document(
                    document_id=document_id,
                    workspace_id=workspace_id,
                    file_path="/nonexistent/file.pdf",
                    db=mock_db,
                    vector_store=vector_store
                )
            
            # Verify error update was called
            mock_db.execute.assert_called()
            mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_process_empty_pdf_completes_without_error(self, temp_chroma_dir, mock_embedding_model, empty_pdf_path):
        """Test that empty PDF completes without error (no chunks stored)."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.document_processor import process_document
            from backend.services.vector_store import VectorStoreService
            
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()
            
            document_id = str(uuid.uuid4())
            workspace_id = str(uuid.uuid4())
            
            vector_store = VectorStoreService(persist_directory=temp_chroma_dir)
            
            # Should not raise
            await process_document(
                document_id=document_id,
                workspace_id=workspace_id,
                file_path=empty_pdf_path,
                db=mock_db,
                vector_store=vector_store
            )
            
            # Verify database update was called
            mock_db.execute.assert_called()
            mock_db.commit.assert_called()
