"""Tests for ChromaDB dependencies installation."""
import importlib.metadata


def test_chromadb_importable():
    """Test that chromadb is importable after installation."""
    import chromadb
    assert chromadb is not None


def test_llama_index_vector_stores_chroma_importable():
    """Test that llama-index-vector-stores-chroma is importable."""
    from llama_index.vector_stores.chroma import ChromaVectorStore
    assert ChromaVectorStore is not None


def test_chromadb_version():
    """Test that chromadb version is >= 1.0.0."""
    version = importlib.metadata.version("chromadb")
    major_version = int(version.split(".")[0])
    assert major_version >= 1, f"Expected chromadb>=1.0.0, got {version}"
