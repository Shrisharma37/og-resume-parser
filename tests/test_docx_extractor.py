"""
tests/test_docx_extractor.py
Unit tests and benchmarks for Phase 3 DOCX extraction and reading-order preservation.
"""

import io
import time
import docx
import pytest
from src.extractors.docx_extractor import extract_docx_data


@pytest.fixture
def sample_docx_bytes():
    """
    Creates an in-memory DOCX file with an interleaved sequence:
    Paragraph 1 (Header) -> Table (Education) -> Paragraph 2 (Experience)
    """
    doc = docx.Document()
    
    # 1. Header Paragraph
    doc.add_paragraph("John Doe\njohn.doe@example.com")
    
    # 2. Interleaved Table (e.g. Education)
    table = doc.add_table(rows=2, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Degree"
    hdr_cells[1].text = "Institution"
    hdr_cells[2].text = "Year"
    
    row_cells = table.rows[1].cells
    row_cells[0].text = "B.Tech"
    row_cells[1].text = "LNCT Bhopal"
    row_cells[2].text = "2024"
    
    # 3. Following Paragraph (e.g. Experience)
    doc.add_paragraph("Work Experience\nSoftware Engineer at Tech Corp")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_docx_preserves_reading_order(sample_docx_bytes):
    """
    Ensures table content is NOT moved to the bottom of the document,
    but retains its exact position between paragraphs.
    """
    data = extract_docx_data(sample_docx_bytes, "resume.docx")
    text = data["text"]

    pos_header = text.find("John Doe")
    pos_table = text.find("LNCT Bhopal")
    pos_experience = text.find("Work Experience")

    assert pos_header != -1, "Header not found"
    assert pos_table != -1, "Table content not found"
    assert pos_experience != -1, "Experience section not found"

    # Crucial assertion: Header < Table < Experience
    assert pos_header < pos_table < pos_experience, (
        f"Reading order violated! Positions: Header={pos_header}, "
        f"Table={pos_table}, Experience={pos_experience}"
    )


def test_docx_latency_under_50ms(sample_docx_bytes):
    """Verifies that DOCX extraction easily executes in <50ms."""
    start = time.perf_counter()
    data = extract_docx_data(sample_docx_bytes, "resume.docx")
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 50.0, f"Extraction was too slow: {duration_ms:.2f}ms"
    assert data["file_name"] == "resume.docx"
    assert data["is_scanned"] is False


def test_legacy_doc_rejection():
    """Verifies legacy binary .doc format is rejected cleanly."""
    with pytest.raises(ValueError, match="Legacy .doc binary format is not supported"):
        extract_docx_data(b"fake doc bytes", "resume.doc")
        