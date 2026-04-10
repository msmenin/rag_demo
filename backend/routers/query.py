"""Query endpoint with SSE streaming for RAG-based question answering."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import re

from backend.schemas.query import QueryRequest
from backend.services.rag_engine import RAGEngine
from backend.database import get_db
from backend.models.workspace import Workspace


router = APIRouter(prefix="/workspace/{workspace_id}/query", tags=["query"])


def validate_uuid(workspace_id: str) -> str:
    """Validate workspace_id is a valid UUID format.
    
    Args:
        workspace_id: Workspace identifier string
        
    Returns:
        Validated workspace_id string
        
    Raises:
        HTTPException: If workspace_id is not a valid UUID
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    if not uuid_pattern.match(workspace_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace_id format: {workspace_id}. Must be a valid UUID."
        )
    return workspace_id


@router.post("/")
async def query(
    workspace_id: str,
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit a natural language query and receive streaming SSE response.
    
    Args:
        workspace_id: UUID of the workspace
        request: Query request with query text and optional document_ids
        db: Database session
        
    Returns:
        StreamingResponse with SSE-formatted chunks
        
    Raises:
        HTTPException: 400 if workspace_id invalid, 404 if workspace not found
    """
    # Validate workspace_id format
    workspace_id = validate_uuid(workspace_id)
    
    # Convert to UUID object for database query
    try:
        workspace_uuid = uuid.UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace_id format: {workspace_id}. Must be a valid UUID."
        )
    
    # Check workspace exists
    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_uuid)
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(
            status_code=404,
            detail=f"Workspace {workspace_id} not found"
        )
    
    # Create RAG engine for this workspace
    rag_engine = RAGEngine(workspace_id=workspace_id)
    
    # Return streaming response
    return StreamingResponse(
        rag_engine.query_stream(
            query=request.query,
            document_ids=request.document_ids
        ),
        media_type="text/event-stream"
    )