"""Vector store service for ChromaDB integration with workspace isolation."""
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext, Document
from typing import List, Dict, Optional
from pathlib import Path

from backend.services.embedding_factory import create_embedding_model


class VectorStoreService:
    """Service for managing vector storage with ChromaDB.
    
    Each workspace gets its own ChromaDB collection for isolation.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize the vector store service.
        
        Args:
            persist_directory: Path to directory for ChromaDB persistence
        """
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embed_model = create_embedding_model()
    
    def get_workspace_collection(self, workspace_id: str):
        """Get or create collection for a workspace.
        
        Args:
            workspace_id: UUID of the workspace
            
        Returns:
            ChromaDB collection for the workspace
        """
        collection_name = f"workspace_{workspace_id}"
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"workspace_id": workspace_id}
        )
    
    async def store_chunks(self, chunks: List[Dict], workspace_id: str) -> int:
        """Store chunks as vectors in workspace collection using direct ChromaDB API.
        
        This bypasses LlamaIndex's document ID generation to preserve our 
        document_id metadata for proper filtering during deletion.
        
        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata' keys
            workspace_id: UUID of the workspace
            
        Returns:
            Number of chunks stored
        """
        collection = self.get_workspace_collection(workspace_id)
        
        if not chunks:
            return 0
        
        # Generate embeddings for all chunks
        texts = [chunk["text"] for chunk in chunks]
        embeddings = [self.embed_model.get_text_embedding(text) for text in texts]
        
        # Generate unique IDs for each chunk
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]
        
        # Extract metadata
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        # Add to collection directly
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        return len(chunks)
    
    async def delete_document_vectors(self, document_id: str, workspace_id: str) -> None:
        """Delete all vectors for a document from workspace collection.
        
        Args:
            document_id: UUID of the document
            workspace_id: UUID of the workspace
        """
        collection = self.get_workspace_collection(workspace_id)
        collection.delete(
            where={"document_id": document_id}
        )
    
    async def query_vectors(
        self, 
        query_text: str, 
        workspace_id: str, 
        top_k: int = 5,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """Query vectors for a workspace.
        
        Args:
            query_text: Query text to search for
            workspace_id: UUID of the workspace
            top_k: Number of results to return
            document_ids: Optional list of document IDs to filter by
            
        Returns:
            List of matching chunks with metadata and scores
        """
        collection = self.get_workspace_collection(workspace_id)
        
        # Generate embedding for query
        query_embedding = self.embed_model.get_query_embedding(query_text)
        
        # Build where filter if document_ids provided
        where_filter = None
        if document_ids:
            where_filter = {"document_id": {"$in": document_ids}}
        
        # Query collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        matches = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                matches.append({
                    "id": doc_id,
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": 1 - results["distances"][0][i]  # Convert distance to similarity
                })
        
        return matches


def get_vector_store_service() -> VectorStoreService:
    """Dependency for FastAPI to get VectorStoreService instance.
    
    Returns:
        VectorStoreService configured with application settings
    """
    from backend.config import settings
    return VectorStoreService(persist_directory=settings.CHROMA_DB_PATH)
