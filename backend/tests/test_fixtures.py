"""Test fixtures functionality."""
import pytest
from pathlib import Path


def test_pdf_fixtures_exist():
    """Test 1: test_small.pdf fixture exists and is readable."""
    pdf_path = Path(__file__).parent / "fixtures" / "test_small.pdf"
    assert pdf_path.exists(), f"test_small.pdf not found at {pdf_path}"

    # Verify it's a valid PDF
    import fitz
    pdf = fitz.open(pdf_path)
    assert pdf.page_count > 0, "test_small.pdf is empty"
    pdf.close()


def test_medium_pdf_properties():
    """Test 2: test_medium.pdf is ~10 pages."""
    pdf_path = Path(__file__).parent / "fixtures" / "test_medium.pdf"
    assert pdf_path.exists(), f"test_medium.pdf not found at {pdf_path}"

    # Verify page count
    import fitz
    pdf = fitz.open(pdf_path)
    assert pdf.page_count == 10, f"test_medium.pdf should have 10 pages, got {pdf.page_count}"
    pdf.close()


def test_fixtures_are_valid_pdfs():
    """Test 3: Fixtures are valid PDFs (not corrupted)."""
    import fitz

    for pdf_name in ["test_small.pdf", "test_medium.pdf"]:
        pdf_path = Path(__file__).parent / "fixtures" / pdf_name
        assert pdf_path.exists(), f"{pdf_name} not found"

        try:
            pdf = fitz.open(pdf_path)
            assert pdf.page_count > 0, f"{pdf_name} has no pages"
            pdf.close()
        except Exception as e:
            pytest.fail(f"{pdf_name} is not a valid PDF: {e}")