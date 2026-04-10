"""Tests for RAG engine service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.rag_engine import RAGEngine


class TestRAGEngine:
    """Tests for RAGEngine class."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store service."""
        mock = MagicMock()
        mock.query_vectors = AsyncMock(return_value=[
            {
                "id": "chunk-1",
                "text": "Machine learning is a subset of AI.",
                "metadata": {
                    "document_id": "doc-123",
                    "page": 1,
                    "document_name": "AI Overview.pdf"
                },
                "score": 0.95
            }
        ])
        return mock
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM instance."""
        mock = MagicMock()
        # Mock streaming response - stream() returns an iterable
        def mock_stream(*args, **kwargs):
            """Mock stream method that yields tokens."""
            for token in ["Machine ", "learning ", "is ", "a ", "subset ", "of ", "AI."]:
                yield token
        
        mock.stream = mock_stream
        return mock
    
    def test_rag_engine_init_with_workspace_id(self):
        """Test RAGEngine initialization with workspace_id."""
        mock_llm = MagicMock()
        engine = RAGEngine(workspace_id="workspace-123", llm=mock_llm)
        assert engine.workspace_id == "workspace-123"
    
    def test_rag_engine_init_without_llm(self):
        """Test RAGEngine initialization creates LLM if not provided."""
        with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
            mock_create_llm.return_value = MagicMock()
            engine = RAGEngine(workspace_id="workspace-123")
            assert mock_create_llm.called
    
    @pytest.mark.asyncio
    async def test_query_stream_retrieves_chunks(self, mock_vector_store, mock_llm):
        """Test query_stream retrieves chunks from vector store."""
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                engine = RAGEngine(workspace_id="workspace-123")
                
                # Collect all SSE messages from the generator
                messages = []
                async for msg in engine.query_stream("What is machine learning?"):
                    messages.append(msg)
                
                # Verify vector store was called
                mock_vector_store.query_vectors.assert_called_once_with(
                    query_text="What is machine learning?",
                    workspace_id="workspace-123",
                    top_k=5,
                    document_ids=None
                )
    
    @pytest.mark.asyncio
    async def test_query_stream_filters_by_document_ids(self, mock_vector_store, mock_llm):
        """Test query_stream passes document_ids filter to vector store."""
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                engine = RAGEngine(workspace_id="workspace-123")
                
                async for _ in engine.query_stream(
                    "What is AI?", 
                    document_ids=["doc-123", "doc-456"]
                ):
                    pass
                
                # Verify document_ids were passed
                mock_vector_store.query_vectors.assert_called_once()
                call_kwargs = mock_vector_store.query_vectors.call_args[1]
                assert call_kwargs["document_ids"] == ["doc-123", "doc-456"]
    
    @pytest.mark.asyncio
    async def test_query_stream_yields_sse_format(self, mock_vector_store, mock_llm):
        """Test query_stream yields SSE-formatted strings."""
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                engine = RAGEngine(workspace_id="workspace-123")
                
                messages = []
                async for msg in engine.query_stream("Test query"):
                    messages.append(msg)
                
                # Verify SSE format: data: {...}
                for msg in messages:
                    assert msg.startswith("data: ")
                    assert msg.endswith("\n\n")
                
                # Last message should be "done"
                last_msg = messages[-1]
                assert '"type": "done"' in last_msg
    
    @pytest.mark.asyncio
    async def test_query_stream_includes_citations(self, mock_vector_store, mock_llm):
        """Test query_stream includes citation information in context."""
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                engine = RAGEngine(workspace_id="workspace-123")
                
                messages = []
                async for msg in engine.query_stream("Test query"):
                    messages.append(msg)
                
                # Verify context was built with metadata by checking successful response
                # The messages should include chunk messages (content from the mock LLM)
                assert len(messages) > 0
                # Check that we got chunk messages (type: "chunk") and not just error
                chunk_messages = [m for m in messages if '"type": "chunk"' in m]
                assert len(chunk_messages) > 0, "Should have received chunk messages from LLM"
    
    @pytest.mark.asyncio
    async def test_query_stream_handles_errors_gracefully(self, mock_vector_store, mock_llm):
        """Test query_stream handles errors without crashing."""
        # Make vector store throw error
        mock_vector_store.query_vectors = AsyncMock(side_effect=Exception("DB error"))
        
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                engine = RAGEngine(workspace_id="workspace-123")
                
                messages = []
                async for msg in engine.query_stream("Test query"):
                    messages.append(msg)
                
                # Should yield an error message, not crash
                assert len(messages) > 0
                error_found = any('"type": "error"' in msg for msg in messages)
                assert error_found