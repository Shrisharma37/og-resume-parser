import re
from typing import Dict, Optional, List

SECTION_SYNONYMS = {
    "profile": [
        "contact", "contact information", "personal details", 
        "bio", "about me", "personal info", "summary", "professional summary"
    ],
    "experience": [
        "work experience", "employment history", "professional experience", 
        "career history", "internships", "volunteer experience", "work history",
        "experience", "employment", "relevant experience"
    ],
    "education": [
        "academic background", "qualifications", "educational background", 
        "degrees", "academics", "education", "educational qualification"
    ],
    "technical_skills": [
        "skills", "core competencies", "technical proficiency", 
        "technologies", "tools & technologies", "technical expertise",
        "technical skills", "skills & tools", "computer skills", "key skills"
    ],
    "projects": [
        "personal projects", "academic projects", "key projects", 
        "portfolio", "open source contributions", "projects"
    ],
    "certifications": [
        "licenses", "courses", "professional certifications", "accreditations",
        "certifications", "certificates"
    ],
    "achievements": [
        "awards", "honors", "accomplishments", "extracurricular activities",
        "achievements", "honors & awards", "awards & achievements"
    ]
}

# Precompute lowercase lookup map
SECTION_LOOKUP: Dict[str, str] = {}
for canonical, synonyms in SECTION_SYNONYMS.items():
    SECTION_LOOKUP[canonical.lower()] = canonical
    SECTION_LOOKUP[canonical.replace('_', ' ').lower()] = canonical
    for s in synonyms:
        SECTION_LOOKUP[s.lower()] = canonical


def normalize_header_text(line: str) -> str:
    """Clean markdown, bullets, numbering, punctuation and trailing whitespace."""
    cleaned = re.sub(r'^[#*\-•\s\d.]+|[#*\-•:\s]+$', '', line).strip()
    return cleaned.lower()


def match_section_header(line: str) -> Optional[str]:
    """Check if a line represents a resume section header."""
    cleaned = normalize_header_text(line)
    if not cleaned or len(cleaned) > 45 or len(cleaned.split()) > 5:
        return None
    
    # Direct match in lookup table
    if cleaned in SECTION_LOOKUP:
        return SECTION_LOOKUP[cleaned]
    
    # Substring / boundary match
    for key, canonical in SECTION_LOOKUP.items():
        if cleaned == key or (len(key) >= 5 and (cleaned.startswith(key) or cleaned.endswith(key))):
            return canonical
            
    return None


def segment_resume_sections(text: str) -> Dict[str, str]:
    """
    Deterministically segments raw resume text into distinct sections
    based on identified section headers.
    """
    lines = text.splitlines()
    sections: Dict[str, List[str]] = {"profile": []}
    current_sec = "profile"
    
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            if current_sec in sections:
                sections[current_sec].append(raw_line)
            continue
            
        header = match_section_header(stripped)
        if header:
            current_sec = header
            if current_sec not in sections:
                sections[current_sec] = []
        else:
            if current_sec not in sections:
                sections[current_sec] = []
            sections[current_sec].append(raw_line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}