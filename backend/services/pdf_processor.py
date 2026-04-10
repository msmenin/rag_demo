"""PDF text extraction service using PyMuPDF4LLM.

Provides functions for extracting text from PDF documents with page numbers
preserved for citation tracking in RAG applications.
"""

from pathlib import Path
from typing import Dict, List

import fitz  # PyMuPDF
import pymupdf4llm


class PDFExtractionError(Exception):
    """Exception raised when PDF extraction fails.

    Used for invalid PDFs, corrupted files, password-protected PDFs,
    and other extraction errors.
    """

    pass


def extract_pdf_text(file_path: str) -> List[Dict]:
    """Extract text from a PDF file with page numbers preserved.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of dictionaries, each containing:
            - 'text': The extracted text for the page
            - 'metadata': Dict with 'page' number (1-indexed)

    Raises:
        PDFExtractionError: If the file is invalid, corrupted, or not a PDF.

    Example:
        >>> pages = extract_pdf_text("document.pdf")
        >>> pages[0]
        {'text': 'First page content...', 'metadata': {'page': 1}}
    """
    # Validate and resolve path
    path = Path(file_path).resolve()

    if not path.exists():
        raise PDFExtractionError(f"File not found: {file_path}")

    if path.is_dir():
        raise PDFExtractionError(f"Path is a directory, not a file: {file_path}")

    try:
        # Use pymupdf4llm for LLM-optimized extraction with page_chunks
        # page_chunks=True returns text split by pages with metadata
        md_text = pymupdf4llm.to_markdown(str(path), page_chunks=True)

        if not md_text:
            return []

        # Convert to our format with 1-indexed page numbers
        pages = []
        for idx, chunk in enumerate(md_text):
            # Each chunk has 'text' and 'metadata' with page number
            if isinstance(chunk, dict):
                text = chunk.get("text", "")
                page_num = chunk.get("metadata", {}).get("page", idx + 1)
            else:
                # Fallback if chunk is just text
                text = str(chunk)
                page_num = idx + 1

            pages.append(
                {
                    "text": text,
                    "metadata": {
                        "page": page_num if page_num > 0 else idx + 1,
                    },
                }
            )

        return pages

    except Exception as e:
        # Check for common PDF errors
        error_msg = str(e).lower()
        if "password" in error_msg or "encrypted" in error_msg:
            raise PDFExtractionError(
                "PDF is password-protected or encrypted"
            ) from e
        if "not a pdf" in error_msg or "invalid" in error_msg:
            raise PDFExtractionError(f"Invalid or corrupted PDF file: {file_path}") from e
        raise PDFExtractionError(f"Failed to extract PDF: {str(e)}") from e


def get_page_count(file_path: str) -> int:
    """Get the number of pages in a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Number of pages in the PDF.

    Raises:
        PDFExtractionError: If the file is invalid or not a PDF.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise PDFExtractionError(f"File not found: {file_path}")

    if path.is_dir():
        raise PDFExtractionError(f"Path is a directory, not a file: {file_path}")

    try:
        doc = fitz.open(str(path))
        count = doc.page_count
        doc.close()
        return count
    except Exception as e:
        raise PDFExtractionError(f"Failed to read PDF: {str(e)}") from e
