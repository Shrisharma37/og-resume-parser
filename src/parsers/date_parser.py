"""
src/parsers/date_parser.py
Centralized date parsing and normalization for education, experience, and projects.
Handles single years, month-year ranges, 'Present' / 'Current', and prevents character-level splitting bugs.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

MONTH_MAP = {
    "jan": "Jan",
    "january": "Jan",
    "feb": "Feb",
    "february": "Feb",
    "mar": "Mar",
    "march": "Mar",
    "apr": "Apr",
    "april": "Apr",
    "may": "May",
    "jun": "Jun",
    "june": "Jun",
    "jul": "Jul",
    "july": "Jul",
    "aug": "Aug",
    "august": "Aug",
    "sep": "Sep",
    "sept": "Sep",
    "september": "Sep",
    "oct": "Oct",
    "october": "Oct",
    "nov": "Nov",
    "november": "Nov",
    "dec": "Dec",
    "december": "Dec",
}

YEAR_TOKEN = r"(?:19|20)\d{2}"
MONTH_NAME_TOKEN = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_TOKEN = rf"(?:{MONTH_NAME_TOKEN}\s*{YEAR_TOKEN}|{YEAR_TOKEN})"
PRESENT_TOKEN = r"(?:Present|Current|Ongoing|Till Date|Now)"

DATE_RANGE_PATTERN = re.compile(
    rf"({DATE_TOKEN})\s*(?:[-–—]|(?:\s+to\s+))\s*({DATE_TOKEN}|{PRESENT_TOKEN})",
    re.IGNORECASE,
)
SINGLE_DATE_PATTERN = re.compile(rf"\b({DATE_TOKEN})\b", re.IGNORECASE)


def normalize_date_token(token: Optional[str]) -> Optional[str]:
    """Cleans and standardizes individual date string components."""
    if not token:
        return None

    token = token.strip().strip(".,; ")
    if re.fullmatch(r"(?:present|current|ongoing|till date|now)", token, re.IGNORECASE):
        return "Present"

    parts = token.split()
    if len(parts) == 2:
        month_part = parts[0].lower().rstrip(".,")
        if month_part in MONTH_MAP:
            return f"{MONTH_MAP[month_part]} {parts[1]}"

    if re.fullmatch(r"(?:19|20)\d{2}", token):
        return token

    return token


def parse_date_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parses start and end dates from a text snippet safely."""
    if not text:
        return None, None

    range_match = DATE_RANGE_PATTERN.search(text)
    if range_match:
        start_str = normalize_date_token(range_match.group(1))
        end_str = normalize_date_token(range_match.group(2))
        return start_str, end_str

    single_matches = list(SINGLE_DATE_PATTERN.finditer(text))
    if len(single_matches) >= 2:
        start_str = normalize_date_token(single_matches[0].group(1))
        end_str = normalize_date_token(single_matches[1].group(1))
        return start_str, end_str
    if len(single_matches) == 1:
        return None, normalize_date_token(single_matches[0].group(1))

    return None, None


def extract_date_range(text: str) -> Optional[Dict[str, Any]]:
    """Extracts start and end dates from a text string."""
    if not text:
        return None

    match = DATE_RANGE_PATTERN.search(text)
    if not match:
        return None

    raw_start = normalize_date_token(match.group(1))
    raw_end = normalize_date_token(match.group(2))
    is_current = bool(raw_end and raw_end.lower() in {"present", "current", "till date", "now"})

    return {
        "start_date": raw_start,
        "end_date": None if is_current else raw_end,
        "is_current": is_current,
        "raw_match": match.group(0),
    }