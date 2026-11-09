"""Consolidated heuristic parser routing canonical sections to domain extractors."""

import re
from typing import Any, Dict, List, Optional

from src.parsers.education_parser import parse_education_section
from src.parsers.experience_parser import parse_experience as _parse_experience
from src.parsers.projects_parser import parse_projects as _parse_projects
from src.parsers.skills_parser import extract_skills
from src.schemas import EducationItem, Experience, Profile, Project


def extract_education(text: str) -> List[EducationItem]:
    """Compatible education extraction interface for the orchestrator."""
    return parse_education_section(text or "")


def extract_profile(raw_text: str, header_text: Optional[str] = None) -> Profile:
    """Best-effort profile extraction from top-of-resume text."""
    header = (header_text or raw_text or "").strip()
    lines = [line.strip() for line in header.splitlines() if line.strip()]
    full_name = lines[0] if lines else None

    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw_text or "")
    phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", raw_text or "")
    linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/in/[^\s]+", raw_text or "", re.I)
    github_match = re.search(r"https?://(?:www\.)?github\.com/[^\s]+", raw_text or "", re.I)
    portfolio_match = re.search(r"https?://[^\s]+", raw_text or "", re.I)

    return Profile(
        full_name=full_name,
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0).strip() if phone_match else None,
        linkedin_url=linkedin_match.group(0) if linkedin_match else None,
        github_url=github_match.group(0) if github_match else None,
        portfolio_url=portfolio_match.group(0) if portfolio_match and not (linkedin_match or github_match) else None,
    )


def extract_list_items(text: str) -> List[str]:
    """Extracts list-based items such as certifications or achievements."""
    if not text:
        return []
    items = []
    for line in text.splitlines():
        clean = re.sub(r"^([•\-\*▪\u2022\u2013\u2014]|\(cid:\d+\)|[\d\.)\s])+", "", line).strip()
        if clean:
            items.append(clean)
    return items


def extract_experience_fallback(text: str) -> List[Experience]:
    """Fallback experience extraction using the deterministic experience parser."""
    records = _parse_experience(text or "")
    parsed: List[Experience] = []
    for rec in records:
        parsed.append(
            Experience(
                company=rec.company or "Unknown Company",
                role=rec.title,
                experience_type="full_time",
                start_date=rec.start_date,
                end_date=rec.end_date,
                description="\n".join(rec.highlights) if rec.highlights else None,
            )
        )
    return parsed


def extract_projects_fallback(text: str) -> List[Project]:
    """Fallback project extraction using the deterministic project parser."""
    records = _parse_projects(text or "")
    parsed: List[Project] = []
    for rec in records:
        desc = rec.description
        if not desc and rec.highlights:
            desc = "\n".join(rec.highlights)
        parsed.append(
            Project(
                title=rec.name or "Untitled Project",
                name=rec.name,
                role=None,
                description=desc,
                technologies=rec.technologies or [],
                link=rec.link,
            )
        )
    return parsed


def parse_canonical_sections(sections: Dict[str, str], raw_text: str = "") -> Dict[str, Any]:
    """Transforms raw section text into structured schema entities."""
    structured_output: Dict[str, Any] = {}

    edu_text = sections.get("education", "")
    structured_output["education"] = [e.model_dump() for e in parse_education_section(edu_text)]

    exp_text = sections.get("experience", "")
    structured_output["experience"] = [w.model_dump() for w in _parse_experience(exp_text)]

    proj_text = sections.get("projects", "")
    structured_output["projects"] = [p.model_dump() for p in _parse_projects(proj_text)]

    skills_text = sections.get("skills", "") or raw_text
    structured_output["skills"] = extract_skills(skills_text)

    return structured_output