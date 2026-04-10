"""End-to-end integration tests for document processing pipeline."""
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.vector_store import get_vector_store_service


@pytest.mark.integration
class TestDocumentPipelineIntegration:
    """End-to-end tests for complete document processing: upload → process → query."""

    async def test_full_pipeline_upload_process_complete(
        self,
        async_client: AsyncClient,
        workspace,
        test_pdf_small,
        db_session: AsyncSession
    ):
        """Test complete document processing pipeline.

        Test flow:
        1. Upload document via API
        2. Poll status until "complete"
        3. Verify document metadata is populated
        4. Verify chunks stored in ChromaDB with correct metadata
        5. Verify retrieval from ChromaDB works
        """
# 1. Upload document
        response = await async_client.post(
            f"/workspace/{workspace.id}/documents/",
            files={"file": ("test.pdf", test_pdf_small, "application/pdf")}
        )

        assert response.status_code == 200
        doc_id = response.json()["id"]
        print(f"Document uploaded with ID: {doc_id}")

        # 2. Poll status until complete (with timeout)
        for attempt in range(30):  # 30 attempts * 1s = 30s timeout
            status_response = await async_client.get(
                f"/workspace/{workspace.id}/documents/{doc_id}/status"
            )

        assert response.status_code == 200
        doc_id = response.json()["id"]
        print(f"Document uploaded with ID: {doc_id}")

        # 2. Poll status until complete (with timeout)
        for attempt in range(30):  # 30 attempts * 1s = 30s timeout
            status_response = await async_client.get(
                f"/workspace/{workspace.id}/documents/{doc_id}/status"
            )
            status = status_response.json()["status"]

            if status == "complete":
                print(f"Processing completed after {attempt + 1} attempts")
                break
            elif status == "error":
                pytest.fail(f"Processing failed: {status_response.json().get('error_message')}")
            elif attempt == 29:
                pytest.fail(f"Processing did not complete within 30 seconds, final status: {status}")

            await asyncio.sleep(1)

        # 3. Verify document metadata is populated
        assert status_response.json()["page_count"] > 0, "page_count should be populated"
        assert status_response.json()["indexed_at"] is not None, "indexed_at should be populated"

# 4. Verify chunks stored in ChromaDB
        vector_store: VectorStoreService = get_vector_store_service()
        collection = vector_store.get_workspace_collection(str(workspace.id))

        # Query all chunks for this document
        results = collection.get(
            where={"document_id": doc_id}
        )

        assert len(results["ids"]) > 0, f"No chunks stored in ChromaDB for document {doc_id}"

        # 5. Verify metadata in chunks is correct
        for metadata in results["metadatas"]:
            assert "page" in metadata, "Chunk metadata must include page number"
            assert "document_id" in metadata, "Chunk metadata must include document_id"
            assert "workspace_id" in metadata, "Chunk metadata must include workspace_id"
            assert "chunk_index" in metadata, "Chunk metadata must include chunk_index"
            assert metadata["document_id"] == doc_id, f"Chunk metadata document_id doesn't match expected: {metadata['document_id']} != {doc_id}"
            assert metadata["workspace_id"] == str(workspace.id), f"Chunk metadata workspace_id doesn't match expected: {metadata['workspace_id']} != {workspace.id}"

    async def test_chunks_stored_with_correct_metadata(
        self,
        async_client: AsyncClient,
        workspace,
        test_pdf_small
    ):
        """Test that chunks are stored with all required metadata.

        Verifies:
        - Page numbers in chunks
        - Document ID in chunks
        - Workspace ID in chunks
        - Chunk index metadata
        """
        # Upload and process document
        response = await async_client.post(
            f"/workspace/{workspace.id}/documents/",
            files={"file": ("test.pdf", test_pdf_small, "application/pdf")}
        )
        doc_id = response.json()["id"]

        # Wait for processing
        for _ in range(30):
            status = await async_client.get(f"/workspace/{workspace.id}/documents/{doc_id}/status")
            if status.json()["status"] == "complete":
                break
            await asyncio.sleep(1)

        # Verify each chunk has complete metadata
        vector_store = get_vector_store_service()
        collection = vector_store.get_workspace_collection(str(workspace.id))
        results = collection.get(where={"document_id": doc_id})

        assert len(results["ids"]) > 0

        # Check metadata completeness
        for idx, metadata in enumerate(results["metadatas"]):
            assert metadata["page"] > 0, f"Chunk {idx} missing or invalid page number"
            assert metadata["document_id"] == doc_id
            assert metadata["workspace_id"] == str(workspace.id)
            assert metadata["chunk_index"] == idx

    async def test_delete_document_removes_vectors(
        self,
        async_client: AsyncClient,
        workspace,
        test_pdf_small
    ):
        """Test that deleting a document removes its vectors from ChromaDB.

        Test flow:
        1. Upload document
        2. Wait for processing complete
        3. Verify vectors exist
        4. Delete document via API
        5. Verify vectors are removed
        """
        # Upload and process
        response = await client.post(
            f"/workspace/{workspace.id}/documents/",
            files={"file": ("test.pdf", test_pdf_small, "application/pdf")}
        )
        doc_id = response.json()["id"]

        # Wait for processing
        for _ in range(30):
            status = await client.get(f"/workspace/{workspace.id}/documents/{doc_id}/status")
            if status.json()["status"] == "complete":
                break
            await asyncio.sleep(1)

        # Verify vectors exist before deletion
        vector_store = get_vector_store_service()
        collection = vector_store.get_workspace_collection(str(workspace.id))
        results_before = collection.get(where={"document_id": doc_id})
        assert len(results_before["ids"]) > 0, "Vectors should exist before deletion"

        # Delete document
        delete_response = await client.delete(
            f"/workspace/{workspace.id}/documents/{doc_id}"
        )
        assert delete_response.status_code == 204

        # Verify vectors removed
        results_after = collection.get(where={"document_id": doc_id})
        assert len(results_after["ids"]) == 0, "Vectors should be removed after document deletion"

    async def test_multiple_documents_in_same_workspace(
        self,
        async_client: AsyncClient,
        workspace,
        test_pdf_small
    ):
        """Test uploading multiple documents to the same workspace.

        Verifies:
        - Multiple documents can be uploaded
        - Each gets a unique document ID
        - All chunks are stored separately
        """
        # Upload first document
        response1 = await async_client.post(
            f"/workspace/{workspace.id}/documents/",
            files={"file": ("test1.pdf", test_pdf_small, "application/pdf")}
        )
        doc_id1 = response1.json()["id"]

        # Wait for first document processing
        for _ in range(30):
            status = await client.get(f"/workspace/{workspace.id}/documents/{doc_id1}/status")
            if status.json()["status"] == "complete":
                break
            await asyncio.sleep(1)

        # Upload second document
        response2 = await async_client.post(
            f"/workspace/{workspace.id}/documents/",
            files={"file": ("test2.pdf", test_pdf_small, "application/pdf")}
        )
        doc_id2 = response2.json()["id"]

        # Verify both documents have unique IDs
        assert doc_id1 != doc_id2

        # Verify both have correct page count
        status1 = await async_client.get(f"/workspace/{workspace.id}/documents/{doc_id1}/status")
        status2 = await async_client.get(f"/workspace/{workspace.id}/documents/{doc_id2}/status")

        assert status1.json()["page_count"] > 0
        assert status2.json()["page_count"] > 0

        # Verify chunks are separate (using ChromaDB query)
        vector_store = get_vector_store_service()
        collection = vector_store.get_workspace_collection(str(workspace.id))

        # Query for document 1 chunks should only return doc 1
        results1 = collection.get(where={"document_id": doc_id1})
        # Query for document 2 chunks should only return doc 2
        results2 = collection.get(where={"document_id": doc_id2})

        assert len(results1["ids"]) > 0
        assert len(results2["ids"]) > 0
        assert all(m["document_id"] == doc_id1 for m in results1["metadatas"])
        assert all(m["document_id"] == doc_id2 for m in results2["metadatas"])

    async def test_nonexistent_document_404(
        self,
        async_client: AsyncClient,
        workspace
    ):
        """Test accessing a non-existent document returns 404."""
        fake_doc_id = "00000000-0000-0000-0000-000000000000"

        response = await async_client.get(
            f"/workspace/{workspace.id}/documents/{fake_doc_id}/status"
        )

        assert response.status_code == 404

        delete_response = await async_client.delete(
            f"/workspace/{workspace.id}/documents/{fake_doc_id}"
        )

        assert response.status_code == 404

        delete_response = await client.delete(
            f"/workspace/{workspace.id}/documents/{fake_doc_id}"
        )

        assert delete_response.status_code == 404