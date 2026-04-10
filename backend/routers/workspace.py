from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from backend.database import get_db
from backend.models.workspace import Workspace
from backend.schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    db: AsyncSession = Depends(get_db)
):
    """Create a new workspace with auto-generated UUID."""
    workspace = Workspace()
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get workspace information by ID."""
    # Validate UUID format
    try:
        uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workspace ID format")
    
    # Query workspace
    result = await db.execute(
        select(Workspace).where(Workspace.id == uuid)
    )
    workspace = result.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return workspace