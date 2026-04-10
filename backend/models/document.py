"""Document model for storing uploaded PDF metadata."""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index
from sqlalchemy.types import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from uuid import uuid4
from backend.database import Base


def generate_uuid():
    """Generate a UUID v4."""
    return uuid4()


def generate_timestamp():
    """Generate current UTC timestamp."""
    return datetime.now(timezone.utc)


class Document(Base):
    """Document model for PDF files within a workspace."""
    __tablename__ = "documents"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=generate_uuid)
    workspace_id = Column(
        Uuid(as_uuid=True), 
        ForeignKey("workspaces.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    page_count = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)  # Bytes
    indexed_at = Column(DateTime, nullable=True)  # For future RAG indexing
    error_message = Column(String, nullable=True)  # Processing errors
    created_at = Column(DateTime, default=generate_timestamp)
    
    # Relationship to workspace
    workspace = relationship("Workspace", back_populates="documents")
    
    # Index for workspace_id query performance
    __table_args__ = (
        Index('idx_documents_workspace', 'workspace_id'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, workspace_id={self.workspace_id}, filename={self.filename})>"
