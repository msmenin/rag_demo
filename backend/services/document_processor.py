"""Document processing pipeline for PDF ingestion.

Orchestrates PDF extraction, chunking, embedding, and vector storage.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from backend.models import Document
from backend.services.pdf_processor import extract_pdf_text, get_page_count, PDFExtractionError
from backend.services.chunker import chunk_text
from backend.services.vector_store import VectorStoreService

if TYPE_CHECKING:
    pass


async def process_document(
    document_id: str,
    workspace_id: str,
    file_path: str,
    db: AsyncSession,
    vector_store: VectorStoreService
) -> None:
    """Process a document: extract text, chunk, embed, store in ChromaDB.
    
    This function is designed to run as a background task after document upload.
    It updates the document record with page count and indexed_at timestamp.
    
    Args:
        document_id: UUID of the document to process
        workspace_id: UUID of the workspace
        file_path: Path to the PDF file
        db: Async database session
        vector_store: Vector store service for embedding storage
        
    Raises:
        PDFExtractionError: If PDF extraction fails
    """
    # Convert string IDs to UUID
    doc_uuid = UUID(document_id)
    
    try:
        # 1. Extract text with page numbers
        pages = extract_pdf_text(file_path)
        
        # 2. Get page count
        page_count = get_page_count(file_path)
        
        # 3. Chunk text with metadata
        chunks = chunk_text(pages, document_id, workspace_id)
        
        # 4. Store chunks in ChromaDB (if any)
        if chunks:
            await vector_store.store_chunks(chunks, workspace_id)
        
        # 5. Update document metadata
        await db.execute(
            update(Document)
            .where(Document.id == doc_uuid)
            .values(
                page_count=page_count,
                indexed_at=datetime.now(timezone.utc)
            )
        )
        await db.commit()
        
    except PDFExtractionError as e:
        # Log error and update document
        await db.execute(
            update(Document)
            .where(Document.id == doc_uuid)
            .values(error_message=str(e))
        )
        await db.commit()
        raise
    except Exception as e:
        # Handle unexpected errors
        await db.execute(
            update(Document)
            .where(Document.id == doc_uuid)
            .values(error_message=f"Processing failed: {str(e)}")
        )
        await db.commit()
        raise
