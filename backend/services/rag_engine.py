"""RAG engine for query processing with LlamaIndex integration."""
import json
import traceback
from typing import AsyncGenerator, Optional, List
from llama_index.core.llms import LLM

from backend.services.vector_store import VectorStoreService, get_vector_store_service
from backend.services.llm_factory import create_llm


class RAGEngine:
    """RAG engine for processing queries with retrieval and generation.
    
    Orchestrates:
    1. Vector retrieval (ChromaDB via VectorStoreService)
    2. Context building from retrieved chunks
    3. LLM streaming response generation
    """
    
    def __init__(self, workspace_id: str, llm: Optional[LLM] = None):
        """Initialize RAG engine for a workspace.
        
        Args:
            workspace_id: UUID of the workspace
            llm: Optional LLM instance (created via factory if not provided)
        """
        self.workspace_id = workspace_id
        self.llm = llm if llm else create_llm()
        self.vector_store: Optional[VectorStoreService] = None
    
    async def _get_vector_store(self) -> VectorStoreService:
        """Get or create vector store service."""
        if self.vector_store is None:
            self.vector_store = get_vector_store_service()
        return self.vector_store
    
    async def query_stream(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> AsyncGenerator[str, None]:
        """Process a query and yield SSE-formatted response chunks.
        
        Args:
            query: Natural language query text
            document_ids: Optional list of document IDs to filter search
            top_k: Number of chunks to retrieve
            
        Yields:
            SSE-formatted strings: "data: {...}\\n\\n"
        """
        try:
            # Get vector store
            vector_store = await self._get_vector_store()
            
            # Retrieve relevant chunks
            chunks = await vector_store.query_vectors(
                query_text=query,
                workspace_id=self.workspace_id,
                top_k=top_k,
                document_ids=document_ids
            )
            
            # Build context string from chunks with metadata
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                metadata = chunk.get("metadata", {})
                doc_name = metadata.get("document_name", "Unknown")
                page = metadata.get("page", "?")
                text = chunk.get("text", "")
                context_parts.append(f"[{i}] {doc_name} (page {page}):\n{text}")
            
            context_str = "\n\n".join(context_parts) if context_parts else "No relevant content found."
            
            # Build prompt for LLM
            prompt = f"""You are a helpful assistant answering questions based on the provided context.
            
Context:
{context_str}

Question: {query}

Please provide a clear and accurate answer based on the context above. When citing information, use the format [1], [2], etc. to reference the sources.

Answer:"""

            # Stream response from LLM
            try:
                # Use async stream complete for string prompts
                response = await self.llm.astream_complete(prompt)
                async for token in response:
                    # Yield each token as SSE chunk
                    chunk_data = json.dumps({
                        "type": "chunk",
                        "content": str(token)
                    })
                    yield f"data: {chunk_data}\n\n"
            except Exception as llm_error:
                # Handle LLM streaming errors
                error_msg = f"LLM error: {str(llm_error)}"
                print(f"[RAG ERROR] {error_msg}")
                print(f"[RAG ERROR] Traceback: {traceback.format_exc()}")
                error_data = json.dumps({
                    "type": "error",
                    "message": error_msg
                })
                yield f"data: {error_data}\n\n"
                return
            
            # Send completion message
            complete_data = json.dumps({"type": "done"})
            yield f"data: {complete_data}\n\n"
            
        except Exception as e:
            # Handle errors gracefully
            error_data = json.dumps({
                "type": "error",
                "message": str(e)
            })
            yield f"data: {error_data}\n\n"