"""
src/parsers/section_mapper.py
Robust section boundary detection and text segmentation.
Maps raw resume text into standardized canonical sections.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern

CONJUNCTION = r"(?:\s+(?:and|&)\s+|\s*[/&]\s*)"

# Raw pattern definitions
_RAW_CANONICAL_SECTIONS: Dict[str, List[str]] = {
    "education": [
        r"education(?:al)?(?:\s+background|\s+qualifications|\s+details|\s+credentials)?",
        r"academic(?:s|\s+background|\s+credentials|\s+qualifications|\s+profile|\s+history)",
        r"qualifications",
        r"degrees?",
    ],
    "experience": [
        r"(?:work|professional|career|relevant|industry)\s+experience",
        r"work\s+history",
        r"employment(?:\s+history)?",
        r"experience",
        r"internships?",
        r"professional\s+background",
    ],
    "projects": [
        r"(?:key|academic|personal|technical|recent|featured)?\s*projects?",
        r"project\s+work",
        r"open\s+source\s+contributions?",
    ],
    "skills": [
        r"(?:technical|core|key|professional|relevant)?\s*skills?",
        r"technical\s+competencies",
        r"technologies(?:\s+and\s+tools|\s*&\s*tools)?",
        rf"skills{CONJUNCTION}competencies",
        rf"skills{CONJUNCTION}abilities",
        rf"tools{CONJUNCTION}technologies",
        r"areas?\s+of\s+expertise",
    ],
    "certifications": [
        rf"certifications?(?:{CONJUNCTION}licenses)?",
        r"certificates?",
        rf"licenses?(?:{CONJUNCTION}certifications)?",
        rf"courses?(?:{CONJUNCTION}trainings?)?",
    ],
    "achievements": [
        rf"achievements?(?:{CONJUNCTION}awards)?",
        rf"awards?(?:{CONJUNCTION}honors|{CONJUNCTION}achievements)?",
        rf"honors?(?:{CONJUNCTION}awards)?",
        r"extracurricular(?:\s+activities)?",
        r"accomplishments?",
    ],
    "publications": [
        r"publications?",
        r"research\s+papers?",
        r"conferences?(?:\s+presentations)?",
    ],
    "languages": [
        r"languages?(?:\s+proficiency)?",
    ],
}

# Pre-compile patterns at module load time for performance
COMPILED_SECTIONS: Dict[str, List[Pattern[str]]] = {
    section: [re.compile(rf"^{pat}$", re.IGNORECASE) for pat in patterns]
    for section, patterns in _RAW_CANONICAL_SECTIONS.items()
}

# Regex to strip common bullet styles, numbering, Roman numerals, and formatting symbols
_PREFIX_STRIP_RE = re.compile(
    r"^(?:[\d]+(?:\.[\d]+)*[\.\)]|[IVXLCDM]+[\.\)]|[\-•\*#\>▪▫◦–—])\s*",
    re.IGNORECASE,
)
_SUFFIX_STRIP_RE = re.compile(r"[:\-\|\~—–]+$")


def _match_section_header(line: str) -> Optional[str]:
    """
    Checks if a stripped line functions as a section header.
    Returns the canonical section key or None.
    """
    clean = line.strip()

    # Headers are typically concise and do not terminate with sentence punctuation
    if not clean or len(clean) > 55 or clean.endswith((".", ";")):
        return None

    # Iteratively remove leading markers/numbering and trailing delimiters
    normalized = _PREFIX_STRIP_RE.sub("", clean).strip()
    normalized = _SUFFIX_STRIP_RE.sub("", normalized).strip()

    if not normalized:
        return None

    for section_name, patterns in COMPILED_SECTIONS.items():
        for pat in patterns:
            if pat.fullmatch(normalized):
                return section_name

    return None


def split_into_sections(raw_text: str) -> Dict[str, str]:
    """
    Segments raw resume text into canonical section chunks.
    Text before the first recognized section heading is assigned to 'profile'.
    """
    if not raw_text or not raw_text.strip():
        return {}

    lines = raw_text.splitlines()
    sections: Dict[str, List[str]] = {"profile": []}
    current_section = "profile"

    for line in lines:
        header_key = _match_section_header(line)
        if header_key:
            current_section = header_key
            if current_section not in sections:
                sections[current_section] = []
        else:
            sections[current_section].append(line)

    result: Dict[str, str] = {}
    for sec, sec_lines in sections.items():
        joined = "\n".join(sec_lines).strip()
        if joined:
            result[sec] = joined

    return result


# Orchestrator and legacy compatibility alias
segment_resume_sections = split_into_sections