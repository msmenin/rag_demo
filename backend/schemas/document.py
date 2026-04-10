"""Pydantic schemas for Document endpoints."""
from pydantic import BaseModel, UUID4, ConfigDict
from datetime import datetime
from typing import Optional


class DocumentResponse(BaseModel):
    """Response schema for document operations."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID4
    workspace_id: UUID4
    filename: str
    file_size: Optional[int] = None
    created_at: datetime
