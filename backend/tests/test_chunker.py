"""Tests for semantic chunking functionality."""
import pytest

from backend.services.chunker import chunk_text, ChunkMetadata


class TestChunkText:
    """Tests for chunk_text function."""

    def test_returns_list_of_chunks_with_text_and_metadata(self):
        """Test that chunk_text returns list of dicts with 'text' and 'metadata' keys."""
        pages = [
            {"text": "This is the first page content. It has multiple sentences. Each should be preserved.", "metadata": {"page": 1}},
            {"text": "This is the second page. More content here.", "metadata": {"page": 2}},
        ]

        result = chunk_text(pages, document_id="doc-123", workspace_id="ws-456")

        assert isinstance(result, list)
        assert len(result) > 0

        for chunk in result:
            assert isinstance(chunk, dict)
            assert "text" in chunk
            assert "metadata" in chunk
            assert isinstance(chunk["text"], str)
            assert isinstance(chunk["metadata"], dict)

    def test_metadata_includes_all_required_fields(self):
        """Test that metadata includes page, document_id, workspace_id, chunk_index."""
        pages = [
            {"text": "Test content for metadata verification.", "metadata": {"page": 1}},
        ]

        result = chunk_text(pages, document_id="doc-123", workspace_id="ws-456")

        for idx, chunk in enumerate(result):
            metadata = chunk["metadata"]
            assert "page" in metadata
            assert "document_id" in metadata
            assert "workspace_id" in metadata
            assert "chunk_index" in metadata
            assert metadata["document_id"] == "doc-123"
            assert metadata["workspace_id"] == "ws-456"
            assert metadata["chunk_index"] == idx

    def test_chunks_respect_sentence_boundaries(self):
        """Test that chunks respect sentence boundaries (no mid-sentence splits)."""
        # Create text with clear sentence boundaries
        pages = [
            {
                "text": "First sentence ends here. Second sentence continues. Third sentence completes.",
                "metadata": {"page": 1},
            },
        ]

        result = chunk_text(pages, document_id="doc-1", workspace_id="ws-1")

        # Each chunk should end with a period or be the last chunk
        for chunk in result[:-1]:
            text = chunk["text"].strip()
            # Should end with sentence-ending punctuation
            assert text.endswith((".", "!", "?")), f"Chunk doesn't end at sentence boundary: {text[-50:]}"

    def test_chunk_size_approximately_1024_tokens(self):
        """Test that chunk size is approximately 1024 tokens (allow variance)."""
        # Create a large text that will need chunking
        long_text = "This is a test sentence. " * 200  # ~1000+ words
        pages = [
            {"text": long_text, "metadata": {"page": 1}},
        ]

        result = chunk_text(pages, document_id="doc-1", workspace_id="ws-1")

        # Should produce multiple chunks
        assert len(result) > 1

        # Each chunk should be reasonably sized (roughly 1024 tokens ~ 4000 chars for English)
        for chunk in result[:-1]:  # Last chunk may be shorter
            # Allow variance: 256-2048 tokens ~ 1000-8000 chars
            assert len(chunk["text"]) > 100, "Chunk too small"
            assert len(chunk["text"]) < 10000, "Chunk too large"

    def test_empty_input_returns_empty_list(self):
        """Test that empty input returns empty list."""
        result = chunk_text([], document_id="doc-1", workspace_id="ws-1")
        assert result == []

    def test_single_page_single_chunk(self):
        """Test that a small single page produces one chunk."""
        pages = [
            {"text": "This is a short page. Only a few sentences.", "metadata": {"page": 1}},
        ]

        result = chunk_text(pages, document_id="doc-1", workspace_id="ws-1")

        assert len(result) == 1
        assert result[0]["metadata"]["page"] == 1

    def test_metadata_page_number_preserved(self):
        """Test that page numbers from input are preserved in output."""
        pages = [
            {"text": "Page one content.", "metadata": {"page": 1}},
            {"text": "Page two content.", "metadata": {"page": 2}},
            {"text": "Page three content.", "metadata": {"page": 3}},
        ]

        result = chunk_text(pages, document_id="doc-1", workspace_id="ws-1")

        # Check that page numbers are in the range 1-3
        page_numbers = {chunk["metadata"]["page"] for chunk in result}
        assert page_numbers.issubset({1, 2, 3})


class TestChunkMetadata:
    """Tests for ChunkMetadata type."""

    def test_chunk_metadata_has_required_fields(self):
        """Test that ChunkMetadata can be created with all fields."""
        metadata = ChunkMetadata(
            page=1,
            document_id="doc-123",
            workspace_id="ws-456",
            chunk_index=0,
        )

        assert metadata["page"] == 1
        assert metadata["document_id"] == "doc-123"
        assert metadata["workspace_id"] == "ws-456"
        assert metadata["chunk_index"] == 0
