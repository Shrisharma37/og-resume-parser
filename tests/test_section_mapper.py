"""
tests/test_section_mapper.py
Unit tests verifying section boundary detection and text segmentation.
"""

from src.parsers.section_mapper import split_into_sections, _match_section_header


def test_header_matching_variations():
    assert _match_section_header("WORK EXPERIENCE") == "experience"
    assert _match_section_header("1. Technical Competencies:") == "skills"
    assert _match_section_header("• Academic Background") == "education"
    assert _match_section_header("Featured Projects") == "projects"
    assert _match_section_header("Awards & Honors") == "achievements"
    assert _match_section_header("Certifications and Licenses:") == "certifications"


def test_false_positive_rejection():
    # Long narrative lines or sentence fragments should NOT be identified as headers
    assert _match_section_header("Experience with building distributed systems using Python.") is None
    assert _match_section_header("Projects included building an AI resume parser.") is None
    assert _match_section_header("Skills: Python, Docker, Kubernetes, AWS, SQL, NoSQL") is None


def test_split_into_sections_flow():
    sample_resume = """
    Jane Doe
    jane.doe@example.com | +91 9876543210
    Bhopal, India

    TECHNICAL SKILLS
    Python, FastAPI, Docker, PyTorch

    WORK HISTORY
    Software Engineer Intern at Tech Corp (2023 - 2024)
    Developed high-throughput document extraction pipelines.

    ACADEMIC BACKGROUND
    B.Tech in Computer Science, LNCT Bhopal

    KEY PROJECTS
    Smart Resume Parser - Python, PyMuPDF
    """

    sections = split_into_sections(sample_resume)

    assert "profile" in sections
    assert "Jane Doe" in sections["profile"]

    assert "skills" in sections
    assert "FastAPI" in sections["skills"]

    assert "experience" in sections
    assert "Tech Corp" in sections["experience"]

    assert "education" in sections
    assert "LNCT Bhopal" in sections["education"]

    assert "projects" in sections
    assert "Smart Resume Parser" in sections["projects"]