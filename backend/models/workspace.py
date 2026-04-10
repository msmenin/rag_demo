from sqlalchemy import Column, String, DateTime
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


class Workspace(Base):
    """Workspace model for isolated document collections."""
    __tablename__ = "workspaces"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=generate_timestamp)
    name = Column(String, nullable=True)
    
    # Relationship to documents (cascade delete)
    documents = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workspace(id={self.id}, created_at={self.created_at})>"