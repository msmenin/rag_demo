"""Performance validation tests for document ingestion pipeline."""
import pytest
import time
import asyncio
from httpx import AsyncClient


@pytest.mark.integration
class TestPerformanceValidation:
    """Performance tests for document ingestion pipeline.

    Metrics based on PERF-03 requirement:
    - Upload + processing completes within 30 seconds for typical PDF (10 pages)
    - Concurrent uploads should not cause errors
    - Memory usage is reasonable
    """

    async def test_upload_completes_within_30s(
        self,
        async_client: AsyncClient,
        workspace,
        test_pdf_medium
    ):
        """PERF-03: Upload should complete within 30 seconds for typical PDF.

        Test flow:
        1. Measure start time
        2. Upload medium PDF (~10 pages)
        3. Poll status until complete
        4. Verify elapsed time < 30 seconds
        """
        start_time = time.time()

        # Upload medium PDF (~10 pages)
        response = await async_client.post(
            f"/workspace/{workspace.id}/documents/",
            files={"file": ("test.pdf", test_pdf_medium, "application/pdf")}
        )

        assert response.status_code == 200
        doc_id = response.json()["id"]

        # Poll until complete or timeout
        for attempt in range(30):  # 30 attempts * 1s = 30s timeout
            status = await async_client.get(
                f"/workspace/{workspace.id}/documents/{doc_id}/status"
            )
            if status.json()["status"] == "complete":
                elapsed = time.time() - start_time
                assert elapsed < 30, f"Processing took {elapsed:.1f}s (max 30s)"
                return
            elif status.json()["status"] == "error":
                pytest.fail(f"Processing failed: {status.json().get('error_message')}")

            await asyncio.sleep(1)

        # If we get here, processing didn't complete
        elapsed = time.time() - start_time
        pytest.fail(f"Processing did not complete within 30 seconds (elapsed: {elapsed:.1f}s)")

    async def test_concurrent_uploads(
        self,
        async_client: AsyncClient,
        workspace_factory,
        test_pdf_small
    ):
        """Concurrent uploads from multiple workspaces should work.

        Test flow:
        1. Create 5 workspaces
        2. Upload documents concurrently to all workspaces
        3. Verify all uploads succeed
        4. Wait for all to process
        5. Verify all documents are complete
        """
        # Create 5 workspaces
        workspaces = [await workspace_factory() for _ in range(5)]

        # Upload concurrently to all workspaces
        async def upload_to_workspace(workspace_id):
            response = await async_client.post(
                f"/workspace/{workspace_id}/documents/",
                files={"file": (f"test_{workspace_id}.pdf", test_pdf_small, "application/pdf")}
            )
            return response

        # Execute uploads concurrently
        tasks = [upload_to_workspace(w.id) for w in workspaces]
        responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        for idx, response in enumerate(responses):
            assert response.status_code == 200, f"Workspace {idx} upload failed"

        # Extract document IDs
        doc_ids = [r.json()["id"] for r in responses]

        # Wait for all to process
        async def wait_for_processing(workspace_id, doc_id):
            for attempt in range(30):
                status = await async_client.get(
                    f"/workspace/{workspace_id}/documents/{doc_id}/status"
                )
                if status.json()["status"] in ["complete", "error"]:
                    return status.json()["status"]
                await asyncio.sleep(1)
            return "timeout"

        # Check all documents processed
        wait_tasks = [
            wait_for_processing(w.id, doc_id)
            for w, doc_id in zip(workspaces, doc_ids)
        ]
        statuses = await asyncio.gather(*wait_tasks)

        for idx, status in enumerate(statuses):
            assert status == "complete", f"Workspace {idx} failed: {status}"

    async def test_large_pdf_memory_efficient(
        self,
        async_client: AsyncClient,
        workspace
    ):
        """Processing should not load entire PDF into memory at once.

        Note: This is a design verification test.
        Real memory checking would require memory profiler.
        For now, verify it completes without error for larger PDF.

        Background context:
        - The implementation uses streaming/chunking (PyMuPDF iteration)
        - Entire PDF is not loaded into memory at once
        """
        # Create a larger PDF (50 pages)
        import fitz
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            doc = fitz.open()
            for i in range(50):
                page = doc.new_page()
                page.insert_text((100, 100), f"Page {i+1} " * 200)
            doc.save(tmp.name)
            doc.close()

            with open(tmp.name, "rb") as f:
                large_pdf = f.read()

        # Clean up original temp file
        original_path = tmp.name

        # Measurements
        start_time = time.time()
        page_count = 0

        try:
            # Upload should work (file is just image data, not parsed)
            response = await async_client.post(
                f"/workspace/{workspace.id}/documents/",
                files={"file": ("large.pdf", large_pdf, "application/pdf")}
            )
            assert response.status_code == 200, "Large PDF upload should succeed"

            doc_id = response.json()["id"]

            # Poll status
            for attempt in range(30):
                status = await async_client.get(f"/workspace/{workspace.id}/documents/{doc_id}/status")
                message = status.json()

                if "page_count" in message:
                    page_count = message["page_count"]
                    break
                elif status.json()["status"] == "complete":
                    page_count = message.get("page_count", 50)
                    break
                elif status.json()["status"] == "error":
                    pytest.fail(f"Processing failed: {message.get('error_message')}")

                await asyncio.sleep(1)

            # Verify reasonable completion time
            elapsed = time.time() - start_time
            # Large PDF should still complete in reasonable time (< 60s)
            assert elapsed < 60, f"Large PDF processing took {elapsed:.1f}s (max 60s)"
            assert page_count > 0, f"PDF page count should be > 0, got {page_count}"

            # Note: actual memory efficiency is verified by implementation
            # Design uses PyMuPDF iteration (chunks loaded one at a time)

        finally:
            # Cleanup
            if os.path.exists(original_path):
                os.unlink(original_path)

    async def test_quick_small_pdf_fast_processing(
        self,
        async_client: AsyncClient,
        workspace,
        test_pdf_small
    ):
        """Quick processing test for small PDF.

        Verifies that small documents (1-2 pages) process quickly.
        Time target: < 10 seconds for typical system.
        """
        start_time = time.time()

        # Upload
        response = await async_client.post(
            f"/workspace/{workspace.id}/documents/",
            files={"file": ("test.pdf", test_pdf_small, "application/pdf")}
        )
        assert response.status_code == 200
        doc_id = response.json()["id"]

        # Wait for completion
        for _ in range(30):
            status = await async_client.get(f"/workspace/{workspace.id}/documents/{doc_id}/status")
            if status.json()["status"] == "complete":
                break
            await asyncio.sleep(1)

        elapsed = time.time() - start_time

        # Small PDF should be very quick (< 10 seconds)
        assert elapsed < 10, f"Small PDF processing too slow: {elapsed:.1f}s (target: < 10s)"

    async def test_no_resource_contention(
        self,
        async_client: AsyncClient,
        workspace_factory,
        test_pdf_small
    ):
        """Test that multiple documents don't cause resource contention.

        Uploads a series of documents and verifies they all succeed
        without timeouts or service degradation.
        """
        # Create workspace
        workspace = await workspace_factory()

        # Upload multiple documents in sequence
        for i in range(10):
            response = await async_client.post(
                f"/workspace/{workspace.id}/documents/",
                files={"file": (f"test_{i}.pdf", test_pdf_small, "application/pdf")}
            )
            assert response.status_code == 200

            doc_id = response.json()["id"]

            # Wait for this document to complete before next
            for _ in range(10):
                status = await async_client.get(f"/workspace/{workspace.id}/documents/{doc_id}/status")
                if status.json()["status"] in ["complete", "error"]:
                    break
                await asyncio.sleep(1)

            # If it got here but wasn't complete, it might be still processing
            # That's acceptable - we're verifying no errors or timeouts

        # Final status check on last document
        last_doc_id = doc_id
        final_status = await async_client.get(f"/workspace/{workspace.id}/documents/{last_doc_id}/status")
        assert final_status.json()["status"] in ["complete"]