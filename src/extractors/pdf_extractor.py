"""
src/extractors/pdf_extractor.py
High-performance PDF text and hyperlink extraction using PyMuPDF (fitz)
with conditional fallback to pdfplumber.
"""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Any, Dict, List, Set

try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        fitz = None
        PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


def _extract_with_pymupdf(file_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts structured text blocks and hyperlinks using PyMuPDF.
    Sorts text blocks by reading order (top-to-bottom, left-to-right).
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page_count = len(doc)
    extracted_pages: List[str] = []
    hyperlinks: Set[str] = set()

    for page_idx in range(page_count):
        page = doc[page_idx]

        # 1. Extract embedded hyperlinks from annotations
        links = page.get_links()
        for link in links:
            uri = link.get("uri")
            if uri and uri.startswith(("http://", "https://", "mailto:")):
                hyperlinks.add(uri)

        # 2. Extract layout-aware text blocks: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type == 0 indicates text (not an image block)
        blocks = page.get_text("blocks")

        # Sort blocks: group by vertical buckets (~15pt), then sort horizontally
        text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
        text_blocks.sort(key=lambda b: (round(b[1] / 15) * 15, b[0]))

        page_text = "\n".join(b[4].strip() for b in text_blocks)
        if page_text:
            extracted_pages.append(page_text)

    doc.close()

    raw_text = "\n\n".join(extracted_pages)
    return {
        "text": raw_text,
        "page_count": page_count,
        "hyperlinks": hyperlinks,
    }


def _extract_with_pdfplumber_fallback(file_bytes: bytes) -> Dict[str, Any]:
    """
    Conditional fallback using pdfplumber when PyMuPDF yields empty or corrupted text.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber is not installed. Skipping fallback.")
        return {"text": "", "page_count": 0, "hyperlinks": set()}

    extracted_pages: List[str] = []
    hyperlinks: Set[str] = set()
    page_count = 0

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_pages.append(text)
            for link in getattr(page, "hyperlinks", []) or []:
                uri = link.get("uri")
                if uri and uri.startswith(("http://", "https://", "mailto:")):
                    hyperlinks.add(uri)

    return {
        "text": "\n\n".join(extracted_pages),
        "page_count": page_count,
        "hyperlinks": hyperlinks,
    }


def extract_pdf_data(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    High-speed PDF extractor.
    Uses PyMuPDF as the primary engine (<15ms) and falls back to pdfplumber
    only if extraction looks empty or corrupted.
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

   # Primary PyMuPDF path (if available)
    if PYMUPDF_AVAILABLE:
        try:
            result = _extract_with_pymupdf(file_bytes)
        except Exception as exc:
            logger.warning("PyMuPDF failed on %s: %s. Attempting pdfplumber fallback.", filename, exc)
            result = _extract_with_pdfplumber_fallback(file_bytes)
    else:
        result = _extract_with_pdfplumber_fallback(file_bytes)

    raw_text = result["text"]
    hyperlinks = result["hyperlinks"]

    # If extraction returned under 50 characters, test fallback before declaring scanned
    if len(raw_text.strip()) < 50:
        fallback_result = _extract_with_pdfplumber_fallback(file_bytes)
        if len(fallback_result["text"].strip()) > len(raw_text.strip()):
            raw_text = fallback_result["text"]
            hyperlinks.update(fallback_result["hyperlinks"])

    # Determine if document is scanned (no machine-readable text)
    is_scanned = len(raw_text.strip()) < 50

    # Append embedded links cleanly for downstream regex/AI parsers
    if hyperlinks:
        raw_text += "\n\nEmbedded Links:\n" + "\n".join(sorted(hyperlinks))

    return {
        "text": raw_text,
        "is_scanned": is_scanned,
        "file_hash": file_hash,
        "file_size": file_size,
        "file_name": filename,
        "page_count": result.get("page_count", 1),
    }


# Backwards compatibility alias
extract_pdf = extract_pdf_data