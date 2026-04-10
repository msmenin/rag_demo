"""Tests for PDF processing functionality."""
import os
import tempfile
from pathlib import Path

import pytest

from backend.services.pdf_processor import (
    extract_pdf_text,
    get_page_count,
    PDFExtractionError,
)


class TestPDFDependency:
    """Test that PDF processing dependencies are installed."""

    def test_pymupdf4llm_importable(self):
        """Test that pymupdf4llm can be imported."""
        import pymupdf4llm

        assert pymupdf4llm is not None

    def test_pymupdf4llm_version(self):
        """Test that pymupdf4llm version is >= 0.0.17."""
        import pymupdf4llm

        # Check version is available and meets minimum
        version = pymupdf4llm.__version__
        major, minor, patch = map(int, version.split(".")[:3])
        assert (major, minor, patch) >= (0, 0, 17), f"Version {version} is less than 0.0.17"


class TestExtractPDFText:
    """Tests for extract_pdf_text function."""

    def test_returns_list_of_page_dicts(self, sample_pdf_path):
        """Test that extract_pdf_text returns list of dicts with 'text' and 'metadata' keys."""
        result = extract_pdf_text(sample_pdf_path)

        assert isinstance(result, list)
        assert len(result) > 0

        for page in result:
            assert isinstance(page, dict)
            assert "text" in page
            assert "metadata" in page
            assert isinstance(page["text"], str)
            assert isinstance(page["metadata"], dict)

    def test_page_metadata_includes_page_number(self, sample_pdf_path):
        """Test that page metadata includes 'page' number (1-indexed)."""
        result = extract_pdf_text(sample_pdf_path)

        for idx, page in enumerate(result):
            assert "page" in page["metadata"]
            assert isinstance(page["metadata"]["page"], int)
            # Page numbers should be 1-indexed
            assert page["metadata"]["page"] == idx + 1

    def test_invalid_pdf_raises_error(self):
        """Test that invalid PDF raises PDFExtractionError with clear message."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"This is not a valid PDF content")
            invalid_path = f.name

        try:
            with pytest.raises(PDFExtractionError) as exc_info:
                extract_pdf_text(invalid_path)
            # Error message should indicate extraction failure
            assert "pdf" in str(exc_info.value).lower() or "extract" in str(exc_info.value).lower()
        finally:
            os.unlink(invalid_path)

    def test_empty_pdf_returns_empty_text(self, empty_pdf_path):
        """Test that PDF with no text content returns pages with empty text (not error)."""
        result = extract_pdf_text(empty_pdf_path)
        # Should return pages but with empty or minimal text
        assert isinstance(result, list)
        # Each page should have empty or whitespace-only text
        for page in result:
            assert "text" in page
            assert page["text"].strip() == ""

    def test_nonexistent_file_raises_error(self):
        """Test that nonexistent file path raises PDFExtractionError."""
        with pytest.raises(PDFExtractionError):
            extract_pdf_text("/nonexistent/path/to/file.pdf")

    def test_directory_path_raises_error(self):
        """Test that passing a directory raises PDFExtractionError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(PDFExtractionError) as exc_info:
                extract_pdf_text(tmpdir)
            assert "directory" in str(exc_info.value).lower() or "not a file" in str(exc_info.value).lower()

    def test_path_traversal_prevented(self):
        """Test that path traversal is prevented."""
        # Create a test file outside the expected area
        with tempfile.TemporaryDirectory() as tmpdir:
            # This should be handled by Path().resolve()
            malicious_path = "../../../etc/passwd"
            with pytest.raises(PDFExtractionError):
                extract_pdf_text(malicious_path)


class TestGetPageCount:
    """Tests for get_page_count function."""

    def test_returns_page_count(self, sample_pdf_path):
        """Test that get_page_count returns correct page count."""
        count = get_page_count(sample_pdf_path)
        assert isinstance(count, int)
        assert count >= 1

    def test_invalid_pdf_raises_error(self):
        """Test that invalid PDF raises PDFExtractionError."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"This is not a valid PDF content")
            invalid_path = f.name

        try:
            with pytest.raises(PDFExtractionError):
                get_page_count(invalid_path)
        finally:
            os.unlink(invalid_path)


class TestPDFExtractionError:
    """Tests for PDFExtractionError exception."""

    def test_accepts_message_string(self):
        """Test that PDFExtractionError accepts message string."""
        error = PDFExtractionError("Test error message")
        assert str(error) == "Test error message"

    def test_inherits_from_exception(self):
        """Test that PDFExtractionError inherits from Exception."""
        assert issubclass(PDFExtractionError, Exception)


# Fixtures
@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF file for testing."""
    import fitz  # PyMuPDF

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "sample.pdf"
        doc = fitz.open()  # Create new PDF
        page = doc.new_page()
        page.insert_text((50, 72), "Sample PDF content for testing")
        doc.save(str(pdf_path))
        doc.close()
        yield str(pdf_path)


@pytest.fixture
def empty_pdf_path():
    """Create an empty PDF file (one page with no text) for testing."""
    import fitz  # PyMuPDF

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "empty.pdf"
        doc = fitz.open()  # Create new PDF
        doc.new_page()  # Add one empty page
        doc.save(str(pdf_path))
        doc.close()
        yield str(pdf_path)
