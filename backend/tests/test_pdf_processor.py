"""Tests for PDF processing functionality."""
import pytest


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
        major, minor, patch = map(int, version.split('.')[:3])
        assert (major, minor, patch) >= (0, 0, 17), f"Version {version} is less than 0.0.17"
