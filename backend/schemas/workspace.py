from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional


class WorkspaceCreate(BaseModel):
    """Schema for creating a workspace (auto-generated ID)."""
    pass


class WorkspaceResponse(BaseModel):
    """Schema for workspace response."""
    id: UUID4
    created_at: datetime
    name: Optional[str] = None
    
    model_config = {"from_attributes": True}