"""Tests for query endpoint."""
import pytest
import uuid
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from backend.models.workspace import Workspace
from backend.services.rag_engine import RAGEngine


@pytest.fixture
async def query_workspace(db_session):
    """Create a test workspace for query tests."""
    workspace = Workspace(id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    return workspace


class TestQueryEndpoint:
    """Tests for POST /workspace/{workspace_id}/query endpoint."""
    
    @pytest.mark.asyncio
    async def test_query_endpoint_returns_streaming_response(self, async_client: AsyncClient, db_session, query_workspace):
        """Test endpoint returns StreamingResponse."""
        async def mock_stream(*args, **kwargs):
            yield 'data: {"type": "chunk", "content": "test"}\n\n'
            yield 'data: {"type": "done"}\n\n'
        
        with patch("backend.routers.query.RAGEngine") as MockRAGEngine:
            mock_engine = MagicMock()
            mock_engine.query_stream = mock_stream
            MockRAGEngine.return_value = mock_engine
            
            response = await async_client.post(
                f"/workspace/{query_workspace.id}/query/",
                json={"query": "test question"}
            )
            
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_query_endpoint_validates_workspace_id_format(self, async_client: AsyncClient, db_session):
        """Test endpoint returns 400 for invalid workspace_id format."""
        response = await async_client.post(
            "/workspace/invalid-uuid/query/",
            json={"query": "test"}
        )
        
        assert response.status_code == 400
        assert "Invalid workspace_id format" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_query_endpoint_returns_404_if_workspace_not_found(self, async_client: AsyncClient, db_session):
        """Test endpoint returns 404 if workspace doesn't exist."""
        response = await async_client.post(
            "/workspace/550e8400-e29b-41d4-a716-446655440001/query/",
            json={"query": "test"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_query_endpoint_validates_request_body(self, async_client: AsyncClient, db_session, query_workspace):
        """Test endpoint validates request body."""
        # Missing query field
        response = await async_client.post(
            f"/workspace/{query_workspace.id}/query/",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_query_endpoint_sse_format(self, async_client: AsyncClient, db_session, query_workspace):
        """Test endpoint sends SSE-formatted messages."""
        async def mock_stream(*args, **kwargs):
            yield 'data: {"type": "chunk", "content": "Hello"}\n\n'
            yield 'data: {"type": "chunk", "content": " world"}\n\n'
            yield 'data: {"type": "done"}\n\n'
        
        with patch("backend.routers.query.RAGEngine") as MockRAGEngine:
            mock_engine = MagicMock()
            mock_engine.query_stream = mock_stream
            MockRAGEngine.return_value = mock_engine
            
            response = await async_client.post(
                f"/workspace/{query_workspace.id}/query/",
                json={"query": "test"}
            )
            
            content = response.text
            
            # Verify SSE format
            lines = content.strip().split('\n\n')
            for line in lines:
                if line:
                    assert line.startswith('data: ')
    
    @pytest.mark.asyncio
    async def test_query_endpoint_workspace_isolation(self, async_client: AsyncClient, db_session, query_workspace):
        """Test endpoint enforces workspace isolation."""
        async def mock_stream(*args, **kwargs):
            yield 'data: {"type": "done"}\n\n'
        
        with patch("backend.routers.query.RAGEngine") as MockRAGEngine:
            mock_engine = MagicMock()
            mock_engine.query_stream = mock_stream
            MockRAGEngine.return_value = mock_engine
            
            await async_client.post(
                f"/workspace/{query_workspace.id}/query/",
                json={"query": "test"}
            )
            
            # Verify RAGEngine was initialized with workspace_id (as string for URL)
            MockRAGEngine.assert_called_once_with(workspace_id=str(query_workspace.id))
    
    @pytest.mark.asyncio
    async def test_query_endpoint_with_document_ids(self, async_client: AsyncClient, db_session, query_workspace):
        """Test endpoint passes document_ids to RAG engine."""
        async def mock_stream(*args, **kwargs):
            yield 'data: {"type": "done"}\n\n'
        
        document_ids = ["doc-123", "doc-456"]
        
        with patch("backend.routers.query.RAGEngine") as MockRAGEngine:
            mock_engine = MagicMock()
            mock_engine.query_stream = MagicMock(return_value=mock_stream())
            MockRAGEngine.return_value = mock_engine
            
            await async_client.post(
                f"/workspace/{query_workspace.id}/query/",
                json={
                    "query": "test",
                    "document_ids": document_ids
                }
            )
            
            # Verify query_stream was called with document_ids
            mock_engine.query_stream.assert_called_once()
            call_kwargs = mock_engine.query_stream.call_args[1]
            assert call_kwargs["document_ids"] == document_ids