"""
src/parsers/date_parser.py
Centralized date parsing and normalization for education, experience, and projects.
Handles single years, month-year ranges, 'Present' / 'Current', and prevents character-level splitting bugs.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

MONTH_MAP = {
    "jan": "Jan", "january": "Jan",
    "feb": "Feb", "february": "Feb",
    "mar": "Mar", "march": "Mar",
    "apr": "Apr", "april": "Apr",
    "may": "May",
    "jun": "Jun", "june": "Jun",
    "jul": "Jul", "july": "Jul",
    "aug": "Aug", "august": "Aug",
    "sep": "Sep", "sept": "Sep", "september": "Sep",
    "oct": "Oct", "october": "Oct",
    "nov": "Nov", "november": "Nov",
    "dec": "Dec", "december": "Dec",
}

DATE_TOKEN = r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2}[\/\.-])\s*)?(?:19|20)\d{2}'
PRESENT_TOKEN = r'(?:Present|Current|Ongoing|Till Date|Now)'

DATE_RANGE_PATTERN = re.compile(
    rf'({DATE_TOKEN})\s*(?:[-–—]|(?:\s+to\s+))\s*({DATE_TOKEN}|{PRESENT_TOKEN})',
    re.IGNORECASE,
)
SINGLE_DATE_PATTERN = re.compile(rf'\b({DATE_TOKEN})\b', re.IGNORECASE)


def normalize_date_token(token: Optional[str]) -> Optional[str]:
    """Cleans and standardizes individual date string components."""
    if not token:
        return None
    token = token.strip()
    if re.match(r'^(?:present|current|ongoing|till date|now)$', token, re.IGNORECASE):
        return "Present"

    parts = token.split()
    if len(parts) == 2:
        m_lower = parts[0].lower().rstrip(".,")
        if m_lower in MONTH_MAP:
            return f"{MONTH_MAP[m_lower]} {parts[1]}"

    return token


def parse_date_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses start and end dates from a text snippet safely.
    Returns (start_date, end_date).
    """
    if not text:
        return None, None

    # 1. Match full range (e.g., 'Oct 2022 - Dec 2026', '2020 to 2024')
    range_match = DATE_RANGE_PATTERN.search(text)
    if range_match:
        start_str = normalize_date_token(range_match.group(1))
        end_str = normalize_date_token(range_match.group(2))
        return start_str, end_str

    # 2. Check for single year or date token (e.g. 'Completed in 2024')
    single_matches = list(SINGLE_DATE_PATTERN.finditer(text))
    if len(single_matches) >= 2:
        start_str = normalize_date_token(single_matches[0].group(1))
        end_str = normalize_date_token(single_matches[1].group(1))
        return start_str, end_str
    elif len(single_matches) == 1:
        return None, normalize_date_token(single_matches[0].group(1))

    return None, None