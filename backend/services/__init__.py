"""Service layer for LLM and embedding providers."""
from backend.services.llm_factory import create_llm, validate_provider_config
from backend.services.embedding_factory import create_embedding_model
from backend.services.pdf_processor import (
    extract_pdf_text,
    get_page_count,
    PDFExtractionError,
)
from backend.services.chunker import chunk_text, ChunkMetadata
from backend.services.vector_store import VectorStoreService, get_vector_store_service
from backend.services.document_processor import process_document

__all__ = [
    "create_llm",
    "validate_provider_config",
    "create_embedding_model",
    "extract_pdf_text",
    "get_page_count",
    "PDFExtractionError",
    "chunk_text",
    "ChunkMetadata",
    "VectorStoreService",
    "get_vector_store_service",
    "process_document",
]
