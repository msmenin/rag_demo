"""Document API endpoints."""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from uuid import UUID
import aiofiles
from backend.database import get_db
from backend.models import Workspace, Document
from backend.schemas import DocumentResponse
from backend.config import settings
from backend.services.document_processor import process_document
from backend.services.vector_store import get_vector_store_service


router = APIRouter(prefix="/workspace/{workspace_id}/documents", tags=["documents"])

# Constants
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/", response_model=DocumentResponse)
async def upload_document(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a PDF document to a workspace with background processing."""
    # Validate workspace ID format
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID format")
    
    # Validate workspace exists
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_uuid)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check document count capacity
    count_result = await db.execute(
        select(func.count(Document.id)).where(Document.workspace_id == workspace_uuid)
    )
    current_count = count_result.scalar() or 0
    
    if current_count >= settings.MAX_DOCUMENTS_PER_WORKSPACE:
        raise HTTPException(
            status_code=429,
            detail=f"Workspace has reached maximum document capacity ({settings.MAX_DOCUMENTS_PER_WORKSPACE}). "
                   f"Delete documents to upload more."
        )
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Sanitize filename to prevent path traversal
    safe_filename = Path(file.filename).name
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Create upload directory
    upload_dir = Path("uploads") / workspace_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Write file
    file_path = upload_dir / safe_filename
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Create document record
    document = Document(
        workspace_id=workspace.id,
        filename=safe_filename,
        file_path=str(file_path),
        file_size=len(content)
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    # Queue background processing
    # Note: We create a new async session for the background task
    # because the current session will be closed after the request
    from backend.database import async_session
    
    async def process_with_new_session():
        async with async_session() as bg_db:
            vector_store = get_vector_store_service()
            await process_document(
                document_id=str(document.id),
                workspace_id=str(workspace.id),
                file_path=str(file_path),
                db=bg_db,
                vector_store=vector_store
            )
    
    background_tasks.add_task(process_with_new_session)
    
    return document


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all documents in a workspace."""
    # Validate workspace ID format
    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID format")
    
    # Validate workspace exists
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_uuid)
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Query documents for this workspace ONLY (isolation guarantee)
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_uuid)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()
    
    return documents


@router.get("/{document_id}/status")
async def get_document_status(
    workspace_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get document processing status."""
    # Validate IDs format
    try:
        doc_uuid = UUID(document_id)
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Query for document with BOTH workspace_id and document_id (isolation guarantee)
    result = await db.execute(
        select(Document)
        .where(Document.id == doc_uuid)
        .where(Document.workspace_id == workspace_uuid)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Determine status
    if document.error_message:
        status = "error"
    elif document.indexed_at:
        status = "complete"
    else:
        status = "processing"
    
    return {
        "id": str(document.id),
        "status": status,
        "page_count": document.page_count,
        "error_message": document.error_message
    }


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    workspace_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a document from a workspace."""
    # Validate IDs format
    try:
        workspace_uuid = UUID(workspace_id)
        document_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Query for document with BOTH workspace_id and document_id (isolation guarantee)
    result = await db.execute(
        select(Document)
        .where(Document.id == document_uuid)
        .where(Document.workspace_id == workspace_uuid)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete vectors from ChromaDB
    vector_store = get_vector_store_service()
    await vector_store.delete_document_vectors(str(document.id), str(workspace_uuid))
    
    # Delete file from disk
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()
    
    # Delete database record
    await db.delete(document)
    await db.commit()
    
    return None
