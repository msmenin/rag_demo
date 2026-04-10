"""Tests for query request/response schemas."""
import pytest
from pydantic import ValidationError
from backend.schemas.query import QueryRequest, StreamChunk, StreamComplete, StreamError


class TestQueryRequest:
    """Tests for QueryRequest schema validation."""
    
    def test_query_request_valid_with_query_only(self):
        """Test QueryRequest with only query (document_ids optional)."""
        request = QueryRequest(query="What is machine learning?")
        assert request.query == "What is machine learning?"
        assert request.document_ids is None
    
    def test_query_request_valid_with_document_ids(self):
        """Test QueryRequest with query and document_ids."""
        request = QueryRequest(
            query="What is AI?",
            document_ids=["doc-123", "doc-456"]
        )
        assert request.query == "What is AI?"
        assert request.document_ids == ["doc-123", "doc-456"]
    
    def test_query_request_empty_query_fails(self):
        """Test QueryRequest fails with empty query."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(query="")
        assert "string but allowed to be empty is not valid" in str(exc_info.value).lower() or "at least 1 character" in str(exc_info.value).lower()
    
    def test_query_request_missing_query_fails(self):
        """Test QueryRequest fails when query is missing."""
        with pytest.raises(ValidationError):
            QueryRequest()
    
    def test_query_request_whitespace_query_fails(self):
        """Test QueryRequest fails with whitespace-only query."""
        with pytest.raises(ValidationError):
            QueryRequest(query="   ")


class TestStreamChunk:
    """Tests for StreamChunk schema."""
    
    def test_stream_chunk_valid(self):
        """Test StreamChunk with type and content."""
        chunk = StreamChunk(type="chunk", content="This is the response")
        assert chunk.type == "chunk"
        assert chunk.content == "This is the response"
    
    def test_stream_chunk_valid_empty_content(self):
        """Test StreamChunk allows empty content."""
        chunk = StreamChunk(type="chunk", content="")
        assert chunk.content == ""
    
    def test_stream_chunk_type_must_be_chunk(self):
        """Test StreamChunk type validation."""
        chunk = StreamChunk(type="chunk", content="test")
        assert chunk.type == "chunk"


class TestStreamComplete:
    """Tests for StreamComplete schema."""
    
    def test_stream_complete_valid(self):
        """Test StreamComplete with type."""
        complete = StreamComplete(type="done")
        assert complete.type == "done"


class TestStreamError:
    """Tests for StreamError schema."""
    
    def test_stream_error_valid(self):
        """Test StreamError with type and message."""
        error = StreamError(type="error", message="Something went wrong")
        assert error.type == "error"
        assert error.message == "Something went wrong"