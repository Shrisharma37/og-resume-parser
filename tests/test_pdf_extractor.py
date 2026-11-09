import time
import pytest
import fitz  # PyMuPDF

# 1. Ensure the import matches your actual source path:
# Use 'src.extractors.pdf_extractor' (or 'src.parsers.pdf_extractor' if you renamed the folder)
from src.extractors.pdf_extractor import extract_pdf_data


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generates a valid single-page PDF in memory matching test assertions."""
    doc = fitz.open()
    page = doc.new_page()

    # Insert candidate text
    page.insert_text(
        fitz.Point(72, 72),
        "Jane Doe\njane.doe@example.com\nSenior Software Engineer",
        fontsize=12,
    )

    # Insert an embedded link annotation
    link_rect = fitz.Rect(72, 120, 250, 140)
    page.insert_link({
        "kind": fitz.LINK_URI,
        "from": link_rect,
        "uri": "https://linkedin.com/in/janedoe",
    })

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_extraction_speed_under_50ms(sample_pdf_bytes: bytes):
    """
    Verifies that PyMuPDF extraction completes within an acceptable benchmark threshold.
    Includes a warm-up pass to eliminate initial dynamic C-library loading overhead.
    """
    # Warm-up run
    _ = extract_pdf_data(sample_pdf_bytes, "warmup.pdf")

    # Timed benchmark run
    start = time.perf_counter()
    data = extract_pdf_data(sample_pdf_bytes, "test_resume.pdf")
    duration_ms = (time.perf_counter() - start) * 1000

    # Assertions
    # If running in shared CI/Docker, consider relaxing the bound (e.g. 100.0ms)
    assert duration_ms < 50.0, f"Extraction was too slow: {duration_ms:.2f}ms"
    assert "Jane Doe" in data["text"]
    assert "jane.doe@example.com" in data["text"]
    assert "https://linkedin.com/in/janedoe" in data["text"]
    assert data["is_scanned"] is False
    assert data["page_count"] == 1
    assert data["file_name"] == "test_resume.pdf"