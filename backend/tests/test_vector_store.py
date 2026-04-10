"""Tests for vector store service with ChromaDB integration."""
import pytest
import tempfile
import os
import uuid
from unittest.mock import patch, MagicMock
from pathlib import Path

# We need to test the vector store service without needing real embeddings
# Mock the embedding model for faster tests


class TestVectorStoreService:
    """Tests for VectorStoreService class."""

    @pytest.fixture
    def temp_chroma_dir(self):
        """Create a temporary directory for ChromaDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def mock_embedding_model(self):
        """Mock the embedding factory to avoid real API calls."""
        from llama_index.core.embeddings import BaseEmbedding
        
        mock = MagicMock(spec=BaseEmbedding)
        # Mock the embedding method
        mock._get_text_embedding = MagicMock(return_value=[0.1] * 1536)
        mock._get_query_embedding = MagicMock(return_value=[0.1] * 1536)
        return mock

    def test_get_workspace_collection_creates_collection_with_correct_name(self, temp_chroma_dir, mock_embedding_model):
        """Test that get_workspace_collection() creates collection with name 'workspace_{uuid}'."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.vector_store import VectorStoreService
            
            service = VectorStoreService(persist_directory=temp_chroma_dir)
            workspace_id = str(uuid.uuid4())
            
            collection = service.get_workspace_collection(workspace_id)
            
            assert collection.name == f"workspace_{workspace_id}"

    def test_get_workspace_collection_includes_workspace_id_metadata(self, temp_chroma_dir, mock_embedding_model):
        """Test that collection metadata includes workspace_id."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.vector_store import VectorStoreService
            
            service = VectorStoreService(persist_directory=temp_chroma_dir)
            workspace_id = str(uuid.uuid4())
            
            collection = service.get_workspace_collection(workspace_id)
            
            assert collection.metadata["workspace_id"] == workspace_id

    @pytest.mark.asyncio
    async def test_store_chunks_adds_vectors_with_metadata(self, temp_chroma_dir, mock_embedding_model):
        """Test that store_chunks() adds vectors with metadata to collection."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.vector_store import VectorStoreService
            
            service = VectorStoreService(persist_directory=temp_chroma_dir)
            workspace_id = str(uuid.uuid4())
            document_id = str(uuid.uuid4())
            
            chunks = [
                {
                    "text": "This is test chunk 1",
                    "metadata": {
                        "document_id": document_id,
                        "workspace_id": workspace_id,
                        "page": 1,
                        "chunk_index": 0
                    }
                },
                {
                    "text": "This is test chunk 2",
                    "metadata": {
                        "document_id": document_id,
                        "workspace_id": workspace_id,
                        "page": 1,
                        "chunk_index": 1
                    }
                }
            ]
            
            result = await service.store_chunks(chunks, workspace_id)
            
            assert result == 2
            
            # Verify chunks were stored
            collection = service.get_workspace_collection(workspace_id)
            assert collection.count() == 2

    @pytest.mark.asyncio
    async def test_delete_document_vectors_removes_by_document_id(self, temp_chroma_dir, mock_embedding_model):
        """Test that delete_document_vectors() removes vectors by document_id filter."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.vector_store import VectorStoreService
            
            service = VectorStoreService(persist_directory=temp_chroma_dir)
            workspace_id = str(uuid.uuid4())
            document_id = str(uuid.uuid4())
            other_doc_id = str(uuid.uuid4())
            
            # Store chunks for two documents
            chunks = [
                {
                    "text": "Document 1 chunk",
                    "metadata": {
                        "document_id": document_id,
                        "workspace_id": workspace_id,
                        "page": 1,
                        "chunk_index": 0
                    }
                },
                {
                    "text": "Document 2 chunk",
                    "metadata": {
                        "document_id": other_doc_id,
                        "workspace_id": workspace_id,
                        "page": 1,
                        "chunk_index": 0
                    }
                }
            ]
            
            await service.store_chunks(chunks, workspace_id)
            
            collection = service.get_workspace_collection(workspace_id)
            assert collection.count() == 2
            
            # Delete vectors for document 1
            await service.delete_document_vectors(document_id, workspace_id)
            
            # Verify only document 2 remains
            assert collection.count() == 1

    def test_concurrent_access_to_different_workspaces(self, temp_chroma_dir, mock_embedding_model):
        """Test that different workspaces have separate collections."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.vector_store import VectorStoreService
            
            service = VectorStoreService(persist_directory=temp_chroma_dir)
            workspace_id_1 = str(uuid.uuid4())
            workspace_id_2 = str(uuid.uuid4())
            
            collection_1 = service.get_workspace_collection(workspace_id_1)
            collection_2 = service.get_workspace_collection(workspace_id_2)
            
            # Collections should have different names
            assert collection_1.name != collection_2.name
            assert collection_1.name == f"workspace_{workspace_id_1}"
            assert collection_2.name == f"workspace_{workspace_id_2}"

    def test_embedding_model_from_factory(self, temp_chroma_dir, mock_embedding_model):
        """Test that embedding model is fetched from embedding factory."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model) as mock_factory:
            from backend.services.vector_store import VectorStoreService
            
            service = VectorStoreService(persist_directory=temp_chroma_dir)
            
            # Verify the factory was called
            mock_factory.assert_called_once()

    def test_get_vector_store_service_dependency(self, temp_chroma_dir, mock_embedding_model):
        """Test the get_vector_store_service dependency function."""
        with patch('backend.services.vector_store.create_embedding_model', return_value=mock_embedding_model):
            from backend.services.vector_store import get_vector_store_service
            
            service = get_vector_store_service()
            assert service is not None
            assert hasattr(service, 'get_workspace_collection')
