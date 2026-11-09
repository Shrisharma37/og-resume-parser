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
    Extracts text using PyMuPDF's built-in layout/column-aware sorting,
    along with embedded hyperlinks.
    """
    extracted_pages: List[str] = []
    hyperlinks: Set[str] = set()

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        page_count = len(doc)
        for page in doc:
            # 1. Extract embedded hyperlinks
            for link in page.get_links():
                uri = link.get("uri")
                if uri and uri.startswith(("http://", "https://", "mailto:")):
                    hyperlinks.add(uri.strip())

            # 2. Extract column-aware sorted text
            # sort=True handles multi-column layout detection natively
            page_text = page.get_text("text", sort=True).strip()
            if page_text:
                extracted_pages.append(page_text)

    return {
        "text": "\n\n".join(extracted_pages),
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
            # layout=True preserves visual positioning/columns in pdfplumber
            text = page.extract_text(layout=True)
            if text and text.strip():
                extracted_pages.append(text.strip())

            for link in getattr(page, "hyperlinks", []) or []:
                uri = link.get("uri")
                if uri and uri.startswith(("http://", "https://", "mailto:")):
                    hyperlinks.add(uri.strip())

    return {
        "text": "\n\n".join(extracted_pages),
        "page_count": page_count,
        "hyperlinks": hyperlinks,
    }


def extract_pdf_data(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    High-speed PDF extractor.
    Uses PyMuPDF as the primary engine (<15ms) and falls back to pdfplumber
    only if extraction fails or returns fewer than 50 characters.
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

    result: Dict[str, Any] = {"text": "", "page_count": 0, "hyperlinks": set()}
    used_fallback = False

    # Attempt PyMuPDF extraction
    if PYMUPDF_AVAILABLE:
        try:
            result = _extract_with_pymupdf(file_bytes)
        except Exception as exc:
            logger.warning("PyMuPDF failed on %s: %s. Switching to fallback.", filename, exc)
            result = _extract_with_pdfplumber_fallback(file_bytes)
            used_fallback = True
    else:
        result = _extract_with_pdfplumber_fallback(file_bytes)
        used_fallback = True

    raw_text = result["text"]
    hyperlinks = result["hyperlinks"]

    # Trigger fallback only if not already executed and text is suspiciously short
    if not used_fallback and len(raw_text.strip()) < 50:
        fallback_result = _extract_with_pdfplumber_fallback(file_bytes)
        if len(fallback_result["text"].strip()) > len(raw_text.strip()):
            raw_text = fallback_result["text"]
            hyperlinks.update(fallback_result["hyperlinks"])
            result["page_count"] = fallback_result.get("page_count", result.get("page_count", 0))

    is_scanned = len(raw_text.strip()) < 50

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