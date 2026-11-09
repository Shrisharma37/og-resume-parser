"""
tests/test_pdf_extractor.py
Unit tests and latency benchmarks for Phase 2 PyMuPDF extraction.
"""

import time
import fitz
import pytest
from src.extractors.pdf_extractor import extract_pdf_data


@pytest.fixture
def sample_pdf_bytes():
    """Generates an in-memory PDF with text, links, and sections."""
    doc = fitz.open()
    page = doc.new_page()

    # Add header
    page.insert_text((50, 50), "Jane Doe\njane.doe@example.com\n+1 555-0199", fontsize=12)

    # Add hyperlink annotation
    link_rect = fitz.Rect(50, 90, 200, 110)
    page.insert_text((50, 105), "LinkedIn Profile", fontsize=10)
    page.insert_link({
        "kind": fitz.LINK_URI,
        "from": link_rect,
        "uri": "https://linkedin.com/in/janedoe",
    })

    # Add body sections
    page.insert_text(
        (50, 140),
        "Education\nBachelor of Technology in Computer Science\nLNCT Bhopal (2020 - 2024)",
        fontsize=11,
    )
    page.insert_text((50, 200), "Skills\nPython, Docker, PyTorch, SQL", fontsize=11)

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def test_pdf_extraction_speed_under_50ms(sample_pdf_bytes):
    """Verifies that PyMuPDF extraction completes well within 50ms."""
    start = time.perf_counter()
    data = extract_pdf_data(sample_pdf_bytes, "test_resume.pdf")
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 50.0, f"Extraction was too slow: {duration_ms:.2f}ms"
    assert "Jane Doe" in data["text"]
    assert "jane.doe@example.com" in data["text"]
    assert "https://linkedin.com/in/janedoe" in data["text"]
    assert data["is_scanned"] is False
    assert data["page_count"] == 1


def test_pdf_hyperlink_extraction(sample_pdf_bytes):
    """Verifies embedded hyperlink extraction from PDF annotations."""
    data = extract_pdf_data(sample_pdf_bytes, "test_resume.pdf")
    assert "https://linkedin.com/in/janedoe" in data["text"]


def test_scanned_pdf_detection():
    """Verifies that empty or image-only PDFs are flagged as scanned."""
    doc = fitz.open()
    doc.new_page()  # Blank page
    empty_bytes = doc.write()
    doc.close()

    data = extract_pdf_data(empty_bytes, "scanned.pdf")
    assert data["is_scanned"] is True