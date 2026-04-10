"""Pydantic schemas for Query endpoints."""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List


class QueryRequest(BaseModel):
    """Request schema for query endpoint."""
    model_config = ConfigDict(from_attributes=True)
    
    query: str = Field(..., min_length=1, description="Natural language query")
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of document IDs to filter search"
    )
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError('Query cannot be empty or whitespace')
        return v


class StreamChunk(BaseModel):
    """SSE message for streaming response chunks."""
    model_config = ConfigDict(from_attributes=True)
    
    type: str = Field(default="chunk", description="Message type")
    content: str = Field(default="", description="Text content")


class StreamComplete(BaseModel):
    """SSE message for stream completion."""
    model_config = ConfigDict(from_attributes=True)
    
    type: str = Field(default="done", description="Message type")


class StreamError(BaseModel):
    """SSE message for stream errors."""
    model_config = ConfigDict(from_attributes=True)
    
    type: str = Field(default="error", description="Message type")
    message: str = Field(..., description="Error description")