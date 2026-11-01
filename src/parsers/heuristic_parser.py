import re
from typing import Dict, Optional, List
from src.schemas import Profile, EducationItem, Project, Experience, TechnicalSkills

EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
PHONE_REGEX = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}'
LINKEDIN_REGEX = r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?'
GITHUB_REGEX = r'https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?'
GENERIC_URL_REGEX = r'https?://[a-zA-Z0-9_.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'

DEGREE_PATTERNS = [
    r'Bachelor(?:[\'\w\s]+)?(?:of\s+[\w\s]+)?',
    r'Master(?:[\'\w\s]+)?(?:of\s+[\w\s]+)?',
    r'B\.?Tech(?:nology)?',
    r'M\.?Tech(?:nology)?',
    r'B\.?S\.?(?:c)?',
    r'M\.?S\.?(?:c)?',
    r'B\.?E\.?',
    r'M\.?E\.?',
    r'BCA',
    r'MCA',
    r'Ph\.?D\.?',
    r'Diploma',
    r'Associate(?:\s+Degree)?'
]

DATE_RANGE_REGEX = r'(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?(?:19|20)\d{2}\s*(?:[-–—to]+\s*(?:(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*)?(?:19|20)\d{2}|Present|Current))?'
GPA_REGEX = r'(?:GPA|CGPA|Grade)[:\s]*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)'


def extract_phone(header_text: str) -> Optional[str]:
    """Strictly extract a valid phone number from the candidate's header section."""
    if not header_text:
        return None

    # 1. Look for explicit phone label (e.g. Phone: +91 9876543210, Mobile: ...)
    label_match = re.search(
        r'(?:phone|mobile|cell|tel|contact|call)[:\s]+(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,5}\)?[\s.-]?\d{3,5}[\s.-]?\d{3,5}\b',
        header_text,
        re.I
    )
    if label_match:
        num = re.sub(r'^(?:phone|mobile|cell|tel|contact|call)[:\s]+', '', label_match.group(0), flags=re.I).strip()
        digits = re.sub(r'\D', '', num)
        if 7 <= len(digits) <= 15:
            return num

    # 2. Strict phone regex with boundary checks
    phone_patterns = [
        r'(?<!\w)(?:\+91[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}(?!\w)',  # Indian 10-digit mobile
        r'(?<!\w)(?:\+1[\s.-]?)?\(?[2-9]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)',  # US format
        r'(?<!\w)\+\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,5}(?!\w)'   # International format
    ]
    
    for pat in phone_patterns:
        match = re.search(pat, header_text)
        if match:
            candidate = match.group(0).strip()
            digits = re.sub(r'\D', '', candidate)
            # Ensure not a year range like 2020-2024
            if 10 <= len(digits) <= 15:
                if not (len(digits) == 8 and candidate.startswith(('19', '20'))):
                    return candidate

    return None


def extract_profile(full_text: str, profile_section_text: str = "") -> Profile:
    """Extract candidate profile using fast deterministic regex and heuristics."""
    # Contact info (email, phone, name) must be restricted to the header block
    header_scope = profile_section_text if profile_section_text.strip() else "\n".join(full_text.splitlines()[:15])
    search_scope = header_scope + "\n" + full_text
    
    email_match = re.search(EMAIL_REGEX, header_scope) or re.search(EMAIL_REGEX, full_text)
    email = email_match.group(0) if email_match else None
    
    # Phone number is strictly extracted from header scope ONLY (never from body/footer)
    phone = extract_phone(header_scope)
    
    # Flexible LinkedIn detection (full URL, shorthand, or label format)
    linkedin_url = None
    m_li = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in/|pub/)?([a-zA-Z0-9_.-]+)/?', search_scope, re.I)
    if m_li:
        linkedin_url = f"https://linkedin.com/in/{m_li.group(1)}"
    else:
        m_li_label = re.search(r'\blinkedin[:\s]+(?:https?://(?:www\.)?linkedin\.com/)?(?:in/|pub/)?([a-zA-Z0-9_.-]+)', search_scope, re.I)
        if m_li_label:
            linkedin_url = f"https://linkedin.com/in/{m_li_label.group(1)}"
            
    # Flexible GitHub detection (full URL, shorthand, or label format)
    github_url = None
    m_gh = re.search(r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/?', search_scope, re.I)
    if m_gh:
        github_url = f"https://github.com/{m_gh.group(1)}"
    else:
        m_gh_label = re.search(r'\bgithub[:\s]+(?:https?://(?:www\.)?github\.com/)?([a-zA-Z0-9_.-]+)', search_scope, re.I)
        if m_gh_label:
            github_url = f"https://github.com/{m_gh_label.group(1)}"
    
    # Portfolio URL: find URL that is neither linkedin nor github
    portfolio_url = None
    all_urls = re.findall(GENERIC_URL_REGEX, search_scope)
    for u in all_urls:
        if "linkedin.com" not in u and "github.com" not in u:
            portfolio_url = u
            break

    # Extract Candidate Name from top lines of document
    full_name = None
    top_lines = [line.strip() for line in full_text.splitlines()[:6] if line.strip()]
    for line in top_lines:
        if re.search(EMAIL_REGEX, line) or re.search(r'https?://', line) or re.search(r'\d{3,}', line):
            continue
        cleaned = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = cleaned.split()
        if 1 <= len(words) <= 4 and not any(w.lower() in ["resume", "curriculum", "vitae", "profile", "contact"] for w in words):
            full_name = cleaned
            break

    # Extract Location heuristic
    location = None
    loc_lines = (profile_section_text or "\n".join(top_lines)).splitlines()
    for line in loc_lines:
        loc_match = re.search(r'\b([A-Z][a-zA-Z\s]+,\s*[A-Z][a-zA-Z\s]+)\b', line)
        if loc_match and not re.search(r'college|university|institute', loc_match.group(1), re.I):
            candidate_loc = loc_match.group(1).strip()
            if candidate_loc != full_name:
                location = candidate_loc
                break

    # Extract Summary / Objective if present in the profile block
    summary = None
    m_sum = re.search(r'(?:summary|professional summary|about me|objective|career objective|profile summary)[:\s-]*\n?', search_scope, re.I)
    if m_sum:
        from src.parsers.section_mapper import match_section_header
        after_header = search_scope[m_sum.end():]
        summary_lines = []
        for line in after_header.splitlines()[:6]:
            stripped = line.strip()
            if not stripped:
                if summary_lines:
                    break
                continue
            if match_section_header(stripped):
                break
            summary_lines.append(stripped)
        if summary_lines:
            summary_candidate = " ".join(summary_lines)
            if len(summary_candidate) > 15:
                summary = summary_candidate

    return Profile(
        full_name=full_name,
        email=email,
        phone=phone,
        location=location,
        linkedin_url=linkedin_url,
        github_url=github_url,
        portfolio_url=portfolio_url,
        summary=summary
    )


def extract_skills(skills_text: str) -> List[str]:
    """
    Extract technical skills strictly from the candidate's designated skills section.
    Splits commas, pipes, bullets, and removes category prefixes.
    """
    if not skills_text:
        return []

    results = []
    lines = skills_text.splitlines()
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
            
        # Strip bullet points
        stripped = re.sub(r'^[•*\-–—]\s*', '', stripped)
        
        # If line contains a category prefix like "Languages:" or "Frameworks & Databases:"
        if ":" in stripped:
            prefix, rest = stripped.split(":", 1)
            if len(prefix.split()) <= 4:
                stripped = rest.strip()
        
        # Split on commas, semicolons, pipes, or bullet separators
        tokens = re.split(r'[,|;•\n]', stripped)
        for token in tokens:
            skill = token.strip()
            # Filter out empty or noise strings
            if skill and len(skill) <= 35 and not skill.endswith(':') and skill.lower() not in ["and", "&", "etc"]:
                if skill not in results:
                    results.append(skill)
                    
    return results


def extract_education(education_text: str) -> List[EducationItem]:
    """Extract education items using heuristic degree, date, and institution detection."""
    if not education_text:
        return []

    items: List[EducationItem] = []
    blocks = [b.strip() for b in re.split(r'\n{2,}', education_text) if b.strip()]
    if not blocks:
        blocks = [education_text]

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
            
        institution = lines[0]
        degree = None
        start_date = None
        end_date = None
        grade = None
        
        # Look for degree pattern
        combined_text = " ".join(lines)
        for deg_pattern in DEGREE_PATTERNS:
            deg_match = re.search(deg_pattern, combined_text, re.IGNORECASE)
            if deg_match:
                degree = deg_match.group(0).strip()
                break

        # Look for dates
        date_match = re.search(DATE_RANGE_REGEX, combined_text)
        if date_match:
            parts = re.split(r'[-–—to]+', date_match.group(0))
            if len(parts) == 2:
                start_date = parts[0].strip()
                end_date = parts[1].strip()
            elif len(parts) == 1:
                end_date = parts[0].strip()

        # Look for GPA
        gpa_match = re.search(GPA_REGEX, combined_text, re.IGNORECASE)
        if gpa_match:
            grade = gpa_match.group(1).strip()

        items.append(EducationItem(
            institution=institution,
            degree=degree,
            field_of_study=None,
            start_date=start_date,
            end_date=end_date,
            grade_or_gpa=grade
        ))

    return items


def extract_list_items(section_text: str) -> List[str]:
    """Extract clean bullet points or lines from list sections (certifications, achievements)."""
    if not section_text:
        return []

    items = []
    for line in section_text.splitlines():
        cleaned = re.sub(r'^[•*\-–—\d.]+\s*', '', line).strip()
        if cleaned and len(cleaned) > 2:
            items.append(cleaned)
    return items


def extract_projects_fallback(projects_text: str) -> List[Project]:
    """Deterministic fallback to extract projects if AI is disabled or fails."""
    if not projects_text:
        return []

    projects = []
    blocks = [b.strip() for b in re.split(r'\n{2,}', projects_text) if b.strip()]
    
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
            
        title = lines[0]
        role = None
        description_parts = []
        technologies = []
        
        for line in lines[1:]:
            if re.search(r'^role[:\s-]*', line, re.I):
                role = re.sub(r'^role[:\s-]*', '', line, flags=re.I).strip()
            elif re.search(r'^technologies[:\s-]*', line, re.I):
                tech_str = re.sub(r'^technologies[:\s-]*', '', line, flags=re.I).strip()
                technologies = [t.strip() for t in re.split(r'[,|;]', tech_str) if t.strip()]
            else:
                description_parts.append(line)
                
        projects.append(Project(
            title=title,
            role=role,
            description=" ".join(description_parts) if description_parts else None,
            technologies=technologies
        ))
        
    return projects


def extract_experience_fallback(experience_text: str) -> List[Experience]:
    """Deterministic fallback to extract work experience if AI is disabled or fails."""
    if not experience_text:
        return []

    experiences = []
    blocks = [b.strip() for b in re.split(r'\n{2,}', experience_text) if b.strip()]
    
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
            
        company = lines[0]
        role = None
        exp_type = "full_time"
        start_date = None
        end_date = None
        description_parts = []
        technologies = []
        
        for line in lines[1:]:
            if re.search(r'^role[:\s-]*', line, re.I):
                role = re.sub(r'^role[:\s-]*', '', line, flags=re.I).strip()
            elif re.search(r'intern|volunteer|contract|part[- ]time', line, re.I):
                if "intern" in line.lower():
                    exp_type = "internship"
                elif "volunteer" in line.lower():
                    exp_type = "volunteer"
                date_match = re.search(DATE_RANGE_REGEX, line)
                if date_match:
                    parts = re.split(r'[-–—to]+', date_match.group(0))
                    if len(parts) == 2:
                        start_date = parts[0].strip()
                        end_date = parts[1].strip()
                    elif len(parts) == 1:
                        end_date = parts[0].strip()
            else:
                description_parts.append(line)

        experiences.append(Experience(
            company=company,
            role=role,
            experience_type=exp_type,
            start_date=start_date,
            end_date=end_date,
            description=" ".join(description_parts) if description_parts else None,
            technologies=technologies
        ))

    return experiences