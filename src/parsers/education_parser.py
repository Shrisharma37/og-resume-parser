"""
src/parsers/education_parser.py
Robust deterministic education parser with accurate institution detection,
degree and field of study separation, GPA/percentage extraction, and date normalization.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from src.parsers.date_parser import parse_date_range
from src.schemas import EducationItem

# Ordered patterns: compound degrees (Bachelor of Technology, etc.) match first
DEGREE_KEYWORDS = [
    r'Bachelor\s+of\s+(?:Technology|Engineering|Science|Commerce|Arts|Business\s+Administration|Computer\s+Applications)',
    r'Master\s+of\s+(?:Technology|Engineering|Science|Commerce|Arts|Business\s+Administration|Computer\s+Applications)',
    r'Bachelor(?:\'s)?(?:\s+Degree)?',
    r'Master(?:\'s)?(?:\s+Degree)?',
    r'B\.?Tech(?:nology)?',
    r'M\.?Tech(?:nology)?',
    r'B\.?S\.?c?',
    r'M\.?S\.?c?',
    r'B\.?E\.?',
    r'M\.?E\.?',
    r'BCA',
    r'MCA',
    r'B\.?B\.?A',
    r'M\.?B\.?A',
    r'Ph\.?D\.?',
    r'Diploma',
    r'Higher Secondary(?:\s+School)?',
    r'Senior Secondary',
    r'Class\s+XII|\b12th\b|\b10th\b',
]

INSTITUTION_KEYWORDS = [
    "university", "institute", "college", "school", "academy", "polytechnic",
    "vidyalaya", "campus", "lnct", "iit", "nit", "iiit", "bits",
]

GRADE_PATTERNS = [
    re.compile(r'(?:CGPA|GPA|Grade|Score)[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)', re.I),
    re.compile(r'([0-9]{2}(?:\.[0-9]+)?)\s*%', re.I),
    re.compile(r'\b([0-9]\.[0-9]{1,2}\s*/\s*(?:4|10)(?:\.0)?)\b', re.I),
]


def extract_degree_and_field(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Identifies degree title and field of study (specialization) cleanly without
    splitting on 'of' inside 'Bachelor of Technology' or 'Master of Science'.
    """
    degree: Optional[str] = None
    field: Optional[str] = None

    # 1. Match core degree name
    for pattern in DEGREE_KEYWORDS:
        match = re.search(rf'\b({pattern})\b', text, re.IGNORECASE)
        if match:
            degree = match.group(1).strip()
            # Look for "in <Field>" immediately after the degree or anywhere on the line
            in_match = re.search(rf'{re.escape(degree)}\s+(?:in|–|-)\s+([^,\n\(\)\|]+)', text, re.I)
            if in_match:
                field = in_match.group(1).strip()
            break

    # 2. Fallback check for field of study keywords if not extracted via "in <Field>"
    if not field:
        field_match = re.search(
            r'\b(?:Computer Science(?: and Engineering)?|Information Technology|'
            r'Mechanical Engineering|Electrical Engineering|Civil Engineering|'
            r'Electronics and Communication|Data Science|Artificial Intelligence|'
            r'Software Engineering)\b',
            text,
            re.I,
        )
        if field_match:
            field = field_match.group(0).strip()

    return degree, field


def is_institution_line(line: str) -> bool:
    """Checks if a given line contains an educational institution name."""
    lower = line.lower()
    return any(k in lower for k in INSTITUTION_KEYWORDS)


def extract_grade(text: str) -> Optional[str]:
    """Extracts GPA, CGPA, or percentage value."""
    for pattern in GRADE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def parse_education_section(education_text: str) -> List[EducationItem]:
    """
    Parses education text into structured EducationItem objects.
    Preserves multiple qualifications and handles both line-based and block formats.
    """
    if not education_text or not education_text.strip():
        return []

    raw_blocks = [b.strip() for b in re.split(r'\n{2,}|\n(?=[•\-\*]\s+)', education_text) if b.strip()]
    if not raw_blocks:
        raw_blocks = [education_text.strip()]

    items: List[EducationItem] = []

    for block in raw_blocks:
        lines = [line.strip().lstrip("•-* ") for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        combined_text = " ".join(lines)
        start_date, end_date = parse_date_range(combined_text)
        grade = extract_grade(combined_text)
        degree, field_of_study = extract_degree_and_field(combined_text)

        # Institution resolution
        institution = None
        for line in lines:
            if is_institution_line(line):
                clean_inst = re.split(r'[,\|(]', line)[0].strip()
                institution = clean_inst
                break

        # Fallback institution to line that is neither degree nor date
        if not institution:
            for line in lines:
                is_deg = degree and degree.lower() in line.lower()
                is_dt = (start_date and start_date in line) or (end_date and end_date in line)
                if not is_deg and not is_dt and len(line) > 3:
                    institution = line
                    break

        if not institution and lines:
            institution = lines[0]

        if institution or degree:
            items.append(
                EducationItem(
                    institution=institution,
                    degree=degree,
                    field_of_study=field_of_study,
                    start_date=start_date,
                    end_date=end_date,
                    grade_or_gpa=grade,
                )
            )

    return items


def parse_education(education_text: str) -> List[EducationItem]:
    """Backward-compatible wrapper for heuristic parser consumers."""
    return parse_education_section(education_text)