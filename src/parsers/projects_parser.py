"""High-performance deterministic parser for technical projects."""

import re
from typing import List, Optional
from pydantic import BaseModel, Field

from src.parsers.date_parser import extract_date_range

BULLET_RE = re.compile(r"^\s*([•\-\*▪\u2022\u2013\u2014]|\(cid:\d+\)|\d+[\.\)])\s*")
TECH_DELIM_RE = re.compile(r"(?:tech(?:nologies)?|tools|stack|built with)[\s:]+(.*)", re.IGNORECASE)


class Project(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    link: Optional[str] = None


def _normalize_iso_date(value: Optional[str]) -> Optional[str]:
    """Normalize month/year strings to ISO-like YYYY-MM values, while preserving current statuses."""
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
        return f"{match.group('year')}-{month_map[match.group('month').lower()]}"

    if re.fullmatch(r"\d{4}", value):
        return value

    return value


def parse_projects(raw_text: str) -> List[Project]:
    """Parses project listings and extracts names, tech stacks, and bullet highlights."""
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    projects: List[Project] = []
    current_proj: Optional[Project] = None

    for line in lines:
        date_range = extract_date_range(line)
        is_bullet = bool(BULLET_RE.match(line))
        clean_text = BULLET_RE.sub("", line).strip()

        tech_match = TECH_DELIM_RE.search(clean_text)
        if tech_match and current_proj:
            raw_techs = tech_match.group(1)
            parsed_techs = [t.strip() for t in re.split(r"[,|/•]", raw_techs) if t.strip()]
            current_proj.technologies.extend(parsed_techs)
            continue

        if is_bullet:
            if not current_proj:
                current_proj = Project(name="Key Projects")
            current_proj.highlights.append(clean_text)
            continue

        if date_range:
            start_value = _normalize_iso_date(date_range.get("start_date"))
            end_value = _normalize_iso_date(date_range.get("end_date"))
            if current_proj and (current_proj.name or current_proj.highlights) and current_proj.start_date is None:
                current_proj.start_date = start_value
                current_proj.end_date = end_value
                continue
            if current_proj and (current_proj.name or current_proj.highlights):
                projects.append(current_proj)

            proj_title = re.sub(date_range.get("raw_match", ""), "", line, flags=re.IGNORECASE)
            proj_title = proj_title.strip().strip(",|-/:") or "Untitled Project"

            current_proj = Project(
                name=proj_title,
                start_date=start_value,
                end_date=end_value,
            )
            continue

        if not current_proj or (current_proj.name and current_proj.highlights):
            if current_proj:
                projects.append(current_proj)

            parts = [p.strip() for p in re.split(r" \| | - | – ", line) if p.strip()]
            proj_name = parts[0]
            current_proj = Project(name=proj_name)

            if len(parts) > 1:
                techs = [t.strip() for t in re.split(r"[,/]", parts[1]) if t.strip()]
                current_proj.technologies.extend(techs)
        else:
            current_proj.highlights.append(line)

    if current_proj and (current_proj.name or current_proj.highlights):
        projects.append(current_proj)

    return projects