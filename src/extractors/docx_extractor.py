"""
src/extractors/docx_extractor.py
Optimized DOCX text and hyperlink extraction preserving document-body reading order.
Traverses paragraphs and tables sequentially via OpenXML body elements.
"""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Any, Dict, List, Set, Union

import docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)


def _extract_hyperlinks_from_paragraph(paragraph: Paragraph, doc: docx.Document) -> Set[str]:
    """
    Extracts embedded hyperlink URLs from a paragraph by inspecting <w:hyperlink> nodes.
    """
    urls: Set[str] = set()
    try:
        for child in paragraph._p:
            if child.tag.endswith("hyperlink"):
                r_id = child.attrib.get(qn("r:id"))
                if r_id and r_id in doc.part.rels:
                    rel = doc.part.rels[r_id]
                    target = getattr(rel, "target_ref", None)
                    if target and target.startswith(("http://", "https://", "mailto:")):
                        urls.add(target)
    except Exception as exc:
        logger.debug("Failed to extract paragraph hyperlinks: %s", exc)
    return urls


def extract_docx_data(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extracts text and hyperlinks from a DOCX file while strictly preserving
    the sequential reading order between paragraphs and tables.
    """
    lower_name = filename.lower()
    if lower_name.endswith(".doc"):
        raise ValueError(
            "Legacy .doc binary format is not supported directly. "
            "Please convert the file to .docx or .pdf."
        )

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

    try:
        doc = docx.Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Failed to open DOCX document '{filename}': {exc}") from exc

    full_text_blocks: List[str] = []
    hyperlinks: Set[str] = set()

    # Iterate through child elements of the document body in order
    for element in doc.element.body:
        # Paragraph element (<w:p>)
        if element.tag.endswith("p"):
            p = Paragraph(element, doc)
            text = p.text.strip()
            if text:
                full_text_blocks.append(text)
            # Extract links in this paragraph
            para_links = _extract_hyperlinks_from_paragraph(p, doc)
            hyperlinks.update(para_links)

        # Table element (<w:tbl>)
        elif element.tag.endswith("tbl"):
            tbl = Table(element, doc)
            for row in tbl.rows:
                # Deduplicate merged cells by stripping and filtering unique cell texts
                row_cells: List[str] = []
                seen_cell_text: Set[str] = set()
                for cell in row.cells:
                    c_text = cell.text.strip()
                    if c_text and c_text not in seen_cell_text:
                        seen_cell_text.add(c_text)
                        row_cells.append(c_text)

                if row_cells:
                    full_text_blocks.append(" | ".join(row_cells))

    # Also inspect document-level relationships for any leftover embedded links
    try:
        for rel in doc.part.rels.values():
            if "hyperlink" in getattr(rel, "reltype", ""):
                target = getattr(rel, "target_ref", None)
                if target and target.startswith(("http://", "https://", "mailto:")):
                    hyperlinks.add(target)
    except Exception:
        pass

    extracted_text = "\n".join(full_text_blocks)

    # Append embedded links cleanly at the end for downstream parsers
    if hyperlinks:
        extracted_text += "\n\nEmbedded Links:\n" + "\n".join(sorted(hyperlinks))

    return {
        "text": extracted_text,
        "is_scanned": False,
        "file_hash": file_hash,
        "file_size": file_size,
        "file_name": filename,
    }


# Backwards compatibility alias
extract_docx = extract_docx_data