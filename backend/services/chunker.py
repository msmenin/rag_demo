"""Semantic chunking service using LlamaIndex SentenceSplitter.

Provides functions for chunking text into semantically meaningful segments
while preserving metadata for citation tracking in RAG applications.
"""

from typing import Dict, List, TypedDict

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter


class ChunkMetadata(TypedDict):
    """Metadata for a text chunk.

    Attributes:
        page: Page number from the source document (1-indexed).
        document_id: UUID of the source document.
        document_name: Filename of the source document.
        workspace_id: UUID of the workspace containing the document.
        chunk_index: Zero-based index of this chunk in the document.
    """

    page: int
    document_id: str
    document_name: str
    workspace_id: str
    chunk_index: int


def chunk_text(
    pages: List[Dict],
    document_id: str,
    document_name: str,
    workspace_id: str,
    chunk_size: int = 1024,
    chunk_overlap: int = 100,
) -> List[Dict]:
    """Chunk text semantically while preserving metadata.

    Uses LlamaIndex SentenceSplitter to respect sentence boundaries
    and create chunks suitable for RAG embedding.

    Args:
        pages: List of page dicts with 'text' and 'metadata' keys.
        document_id: UUID of the source document.
        document_name: Filename of the source document.
        workspace_id: UUID of the workspace.
        chunk_size: Target chunk size in tokens (default 1024).
        chunk_overlap: Overlap between chunks in tokens (default 100).

    Returns:
        List of chunk dicts, each containing:
            - 'text': The chunk text content
            - 'metadata': ChunkMetadata with page, document_id, document_name, workspace_id, chunk_index

    Example:
        >>> pages = [{"text": "Page 1 content...", "metadata": {"page": 1}}]
        >>> chunks = chunk_text(pages, "doc-uuid", "document.pdf", "ws-uuid")
        >>> chunks[0]
        {'text': 'Page 1 content...', 'metadata': {'page': 1, 'document_id': '...', 'document_name': 'document.pdf', ...}}
    """
    if not pages:
        return []

    # Create LlamaIndex documents from pages
    documents = [
        Document(text=page["text"], metadata={"page": page["metadata"]["page"]})
        for page in pages
        if page.get("text")  # Skip empty pages
    ]

    if not documents:
        return []

    # Create sentence-aware splitter
    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Split documents into nodes
    nodes = splitter.get_nodes_from_documents(documents)

    # Convert to our format with full metadata
    chunks = []
    for idx, node in enumerate(nodes):
        chunks.append(
            {
                "text": node.text,
                "metadata": ChunkMetadata(
                    page=node.metadata.get("page", 1),
                    document_id=document_id,
                    document_name=document_name,
                    workspace_id=workspace_id,
                    chunk_index=idx,
                ),
            }
        )

    return chunks
