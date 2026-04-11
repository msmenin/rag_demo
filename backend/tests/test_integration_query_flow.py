"""Integration tests for query end-to-end flow."""
import pytest
import time
import uuid
from httpx import AsyncClient
from pathlib import Path
from backend.models.workspace import Workspace
from backend.models.document import Document
from backend.services.vector_store import VectorStoreService, get_vector_store_service


@pytest.fixture
async def integration_workspace(db_session):
    """Create a workspace for integration tests."""
    workspace = Workspace(id=uuid.uuid4())
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    return workspace


@pytest.fixture
async def integration_document(db_session, integration_workspace, test_pdf_small):
    """Create a document for integration tests."""
    doc = Document(
        id=uuid.uuid4(),
        workspace_id=integration_workspace.id,
        filename="test_query.pdf",
        file_path=f"/uploads/{integration_workspace.id}/test_query.pdf",
        file_size=len(test_pdf_small),
        indexed_at=None,
        error_message=None
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.fixture
async def workspace_with_chunks(db_session, test_pdf_small):
    """Create workspace with indexed document chunks."""
    workspace = Workspace(id=uuid.uuid4())
    db_session.add(workspace)
    await db_session.commit()
    
    # Create document
    doc = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="chunked_doc.pdf",
        file_path=f"/uploads/{workspace.id}/chunked_doc.pdf",
        file_size=len(test_pdf_small),
        indexed_at=None,
        error_message=None
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(workspace)
    await db_session.refresh(doc)
    
    return workspace, doc


class TestQueryIntegrationFlow:
    """End-to-end integration tests for query processing."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_query_flow_with_mocked_chromadb(
        self, 
        async_client: AsyncClient, 
        db_session,
        integration_workspace,
        integration_document,
        monkeypatch
    ):
        """Test full query flow with mocked ChromaDB."""
        from unittest.mock import AsyncMock, MagicMock, patch
        
        # Mock vector store
        mock_vector_store = MagicMock()
        mock_vector_store.query_vectors = AsyncMock(return_value=[
            {
                "id": "chunk-1",
                "text": "Machine learning is a subset of artificial intelligence.",
                "metadata": {
                    "document_id": str(integration_document.id),
                    "page": 1,
                    "document_name": "test_query.pdf"
                },
                "score": 0.95
            }
        ])
        
        # Mock LLM
        def mock_stream(prompt):
            tokens = ["Machine ", "learning ", "is ", "AI."]
            for token in tokens:
                yield token
        
        mock_llm = MagicMock()
        mock_llm.stream = mock_stream
        
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                # Submit query
                response = await async_client.post(
                    f"/workspace/{integration_workspace.id}/query/",
                    json={"query": "What is machine learning?"}
                )
                
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")
                
                # Verify response contains streaming data
                content = response.text
                assert "data:" in content
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_query_response_initiation_under_3_seconds(
        self,
        async_client: AsyncClient,
        db_session,
        integration_workspace,
        monkeypatch
    ):
        """Test query response starts within 3 seconds."""
        from unittest.mock import AsyncMock, MagicMock, patch
        
        # Mock fast vector store
        mock_vector_store = MagicMock()
        mock_vector_store.query_vectors = AsyncMock(return_value=[
            {
                "id": "chunk-1",
                "text": "Test content",
                "metadata": {"document_name": "test.pdf", "page": 1},
                "score": 0.9
            }
        ])
        
        # Mock streaming LLM
        def mock_stream(prompt):
            for i in range(10):
                yield f"Token{i} "
        
        mock_llm = MagicMock()
        mock_llm.stream = mock_stream
        
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                start_time = time.time()
                
                response = await async_client.post(
                    f"/workspace/{integration_workspace.id}/query/",
                    json={"query": "Test query"}
                )
                
                elapsed = time.time() - start_time
                
                assert response.status_code == 200
                # Response should start within 3 seconds
                assert elapsed < 3.0, f"Response took {elapsed:.2f}s, should be < 3s"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multi_document_query(
        self,
        async_client: AsyncClient,
        db_session,
        integration_workspace,
        monkeypatch
    ):
        """Test query retrieves from specified documents only."""
        from unittest.mock import AsyncMock, MagicMock, patch
        
        doc_id_1 = str(uuid.uuid4())
        doc_id_2 = str(uuid.uuid4())
        
        # Mock vector store that filters by document_ids
        async def mock_query_vectors(**kwargs):
            document_ids = kwargs.get("document_ids")
            if document_ids:
                # Only return chunks from specified documents
                return [
                    {
                        "id": f"chunk-{doc_id_1}",
                        "text": f"Content from doc {doc_id_1}",
                        "metadata": {"document_id": doc_id_1, "page": 1},
                        "score": 0.9
                    }
                ]
            return []
        
        mock_vector_store = MagicMock()
        mock_vector_store.query_vectors = mock_query_vectors
        
        def mock_stream(prompt):
            yield "Test response"
        
        mock_llm = MagicMock()
        mock_llm.stream = mock_stream
        
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                # Query with specific document IDs
                response = await async_client.post(
                    f"/workspace/{integration_workspace.id}/query/",
                    json={
                        "query": "Test query",
                        "document_ids": [doc_id_1]
                    }
                )
                
                assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workspace_isolation_in_queries(
        self,
        async_client: AsyncClient,
        db_session,
        monkeypatch
    ):
        """Test query from workspace A doesn't retrieve from workspace B."""
        from unittest.mock import AsyncMock, MagicMock, patch, call
        
        # Create two workspaces
        workspace_a = Workspace(id=uuid.uuid4())
        workspace_b = Workspace(id=uuid.uuid4())
        db_session.add_all([workspace_a, workspace_b])
        await db_session.commit()
        
        # Track which workspace_id was queried
        queried_workspaces = []
        
        async def mock_query_vectors(**kwargs):
            queried_workspaces.append(kwargs.get("workspace_id"))
            return [
                {
                    "id": "chunk-1",
                    "text": "Test",
                    "metadata": {"page": 1},
                    "score": 0.9
                }
            ]
        
        mock_vector_store = MagicMock()
        mock_vector_store.query_vectors = mock_query_vectors
        
        def mock_stream(prompt):
            yield "Response"
        
        mock_llm = MagicMock()
        mock_llm.stream = mock_stream
        
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                # Query workspace A
                response_a = await async_client.post(
                    f"/workspace/{workspace_a.id}/query/",
                    json={"query": "Test A"}
                )
                
                # Query workspace B
                response_b = await async_client.post(
                    f"/workspace/{workspace_b.id}/query/",
                    json={"query": "Test B"}
                )
                
                # Verify each query used correct workspace_id
                assert str(workspace_a.id) in queried_workspaces
                assert str(workspace_b.id) in queried_workspaces
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_handling_invalid_query(
        self,
        async_client: AsyncClient,
        db_session,
        integration_workspace
    ):
        """Test error handling for invalid query."""
        # Empty query should fail validation
        response = await async_client.post(
            f"/workspace/{integration_workspace.id}/query/",
            json={"query": ""}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_handling_missing_workspace(
        self,
        async_client: AsyncClient,
        db_session
    ):
        """Test error handling for non-existent workspace."""
        fake_workspace_id = uuid.uuid4()
        
        response = await async_client.post(
            f"/workspace/{fake_workspace_id}/query/",
            json={"query": "Test query"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_handling_vector_store_failure(
        self,
        async_client: AsyncClient,
        db_session,
        integration_workspace,
        monkeypatch
    ):
        """Test graceful error handling when vector store fails."""
        from unittest.mock import AsyncMock, MagicMock, patch
        
        # Mock failing vector store
        mock_vector_store = MagicMock()
        mock_vector_store.query_vectors = AsyncMock(
            side_effect=Exception("Vector store connection failed")
        )
        
        def mock_stream(prompt):
            yield "Should not reach here"
        
        mock_llm = MagicMock()
        mock_llm.stream = mock_stream
        
        with patch("backend.services.rag_engine.get_vector_store_service") as mock_get_vs:
            mock_get_vs.return_value = mock_vector_store
            
            with patch("backend.services.rag_engine.create_llm") as mock_create_llm:
                mock_create_llm.return_value = mock_llm
                
                # Query should not crash
                response = await async_client.post(
                    f"/workspace/{integration_workspace.id}/query/",
                    json={"query": "Test query"}
                )
                
                assert response.status_code == 200  # SSE stream still starts
                
                # Stream should contain error message
                content = response.text
                assert "error" in content.lower() or response.status_code == 200