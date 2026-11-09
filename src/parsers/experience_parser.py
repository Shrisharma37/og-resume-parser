"""High-performance deterministic parser for work experience sections."""

import re
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from src.parsers.date_parser import extract_date_range

COMMON_ROLE_KEYWORDS = {
    "engineer", "developer", "architect", "lead", "manager", "director",
    "intern", "consultant", "analyst", "specialist", "administrator",
    "designer", "scientist", "head", "officer", "vp", "president", "fellow",
    "associate", "coordinator", "strategist", "programmer", "technician"
}

ORG_INDICATORS = {
    "inc", "corp", "corporation", "ltd", "limited", "llc", "gmbh",
    "technologies", "tech", "solutions", "systems", "labs", "software",
    "services", "studio", "group", "holdings", "co", "company"
}

BULLET_RE = re.compile(r"^\s*([•\-\*▪\u2022\u2013\u2014]|\(cid:\d+\)|\d+[\.\)])\s*")


class WorkExperience(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    highlights: List[str] = Field(default_factory=list)


def _clean_token(text: str) -> str:
    return text.strip().strip(",|-/:")


def _is_probable_role(candidate: str) -> bool:
    tokens = set(re.findall(r"\b[a-zA-Z]+\b", candidate.lower()))
    return bool(tokens & COMMON_ROLE_KEYWORDS)


def _is_probable_company(candidate: str) -> bool:
    tokens = set(re.findall(r"\b[a-zA-Z]+\b", candidate.lower()))
    return bool(tokens & ORG_INDICATORS)


def _split_compound_header(line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Disambiguates single-line headers like 'Senior Engineer | Google | Mountain View, CA'."""
    delimiters = [" | ", " - ", " – ", " — ", " // ", " at "]
    parts = None

    for d in delimiters:
        if d in line:
            parts = [p.strip() for p in line.split(d) if p.strip()]
            break

    if not parts:
        parts = [p.strip() for p in line.split(",") if p.strip()]

    if not parts:
        return None, None, None

    role, company, loc = None, None, None

    if len(parts) == 1:
        text = parts[0]
        if _is_probable_role(text):
            role = text
        else:
            company = text
    elif len(parts) == 2:
        p0, p1 = parts[0], parts[1]
        if _is_probable_role(p0) and not _is_probable_role(p1):
            role, company = p0, p1
        elif _is_probable_company(p0) or not _is_probable_role(p0):
            company, role = p0, p1
        else:
            role, company = p0, p1
    else:
        # 3 or more elements (Role, Company, Location)
        p0, p1, p2 = parts[0], parts[1], parts[2]
        if _is_probable_role(p0):
            role = p0
            company = p1
        else:
            company = p0
            role = p1
        loc = p2

    return role, company, loc


def _normalize_iso_date(value: Optional[str]) -> Optional[str]:
    """Normalizes month-year values to an ISO-like YYYY-MM string for downstream consumers."""
    if not value:
        return None

    value = value.strip()
    if re.fullmatch(r"(?:Present|Current|Ongoing|Till Date|Now)", value, re.IGNORECASE):
        return None

    match = re.fullmatch(r"(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*(?P<year>\d{4})", value, re.IGNORECASE)
    if match:
        month_map = {
            "jan": "01", "january": "01",
            "feb": "02", "february": "02",
            "mar": "03", "march": "03",
            "apr": "04", "april": "04",
            "may": "05",
            "jun": "06", "june": "06",
            "jul": "07", "july": "07",
            "aug": "08", "august": "08",
            "sep": "09", "sept": "09", "september": "09",
            "oct": "10", "october": "10",
            "nov": "11", "november": "11",
            "dec": "12", "december": "12",
        }
        month_key = match.group("month").lower()
        return f"{match.group('year')}-{month_map[month_key]}"

    if re.fullmatch(r"\d{4}", value):
        return value

    return value


def parse_experience(raw_text: str) -> List[WorkExperience]:
    """Parses experience text into structured records within < 10 ms."""
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    records: List[WorkExperience] = []
    current_record: Optional[WorkExperience] = None

    i = 0
    while i < len(lines):
        line = lines[i]

        date_range = extract_date_range(line)

        if date_range:
            start_value = _normalize_iso_date(date_range.get("start_date"))
            end_value = _normalize_iso_date(date_range.get("end_date"))
            is_current = bool(date_range.get("is_current", False))

            if current_record and (current_record.title or current_record.company or current_record.highlights):
                if current_record.start_date is None and current_record.title is not None:
                    current_record.start_date = start_value
                    current_record.end_date = end_value
                    current_record.is_current = is_current
                    current_record = current_record
                else:
                    records.append(current_record)
                    current_record = WorkExperience(
                        start_date=start_value,
                        end_date=end_value,
                        is_current=is_current,
                    )
            else:
                if current_record is None:
                    current_record = WorkExperience()
                current_record.start_date = start_value
                current_record.end_date = end_value
                current_record.is_current = is_current

            clean_anchor = re.sub(date_range.get("raw_match", ""), "", line, flags=re.IGNORECASE).strip()
            clean_anchor = _clean_token(clean_anchor)
            if clean_anchor:
                r, c, loc = _split_compound_header(clean_anchor)
                if r and not current_record.title:
                    current_record.title = r
                if c and not current_record.company:
                    current_record.company = c
                if loc and not current_record.location:
                    current_record.location = loc

            i += 1
            continue

        is_bullet = bool(BULLET_RE.match(line))
        clean_text = BULLET_RE.sub("", line).strip()

        if is_bullet:
            if not current_record:
                current_record = WorkExperience()
            current_record.highlights.append(clean_text)
            i += 1
            continue

        if current_record and current_record.title and current_record.company and current_record.start_date and _is_probable_role(line):
            records.append(current_record)
            current_record = WorkExperience()

        if not current_record:
            current_record = WorkExperience()

        if not current_record.title or not current_record.company:
            r, c, loc = _split_compound_header(line)
            if r and not current_record.title:
                current_record.title = r
            if c and not current_record.company:
                current_record.company = c
            if loc and not current_record.location:
                current_record.location = loc
        else:
            current_record.highlights.append(line)

        i += 1

    if current_record and (current_record.title or current_record.company or current_record.highlights):
        records.append(current_record)

    return records