"""
Unit and benchmark tests for Phase 6 Skills Parser.
Validates normalization, false-positive prevention, and execution speed.
"""

import time
import pytest
from src.parsers.skills_parser import extract_skills


def test_alias_normalization():
    raw_input = (
        "Languages: JS, Python, Golang, Cpp, C#.\n"
        "Frameworks: ReactJS, node.js, sklearn, k8s, Postgres, mongo."
    )
    result = extract_skills(raw_input)

    assert "JavaScript" in result["languages"]
    assert "Python" in result["languages"]
    assert "Go" in result["languages"]
    assert "C++" in result["languages"]
    assert "C#" in result["languages"]

    assert "React" in result["frameworks_libraries"]
    assert "Node.js" in result["frameworks_libraries"]
    assert "Scikit-Learn" in result["frameworks_libraries"]

    assert "Kubernetes" in result["cloud_devops"]
    assert "PostgreSQL" in result["databases"]
    assert "MongoDB" in result["databases"]


def test_false_positive_prevention():
    # 'Go' should not match inside standard prose words; 'c' lowercase should be skipped
    narrative_text = "Good communication skills. Developed a deep passion for coding."
    result = extract_skills(narrative_text)

    assert "Go" not in result["languages"]
    assert "C" not in result["languages"]


def test_single_character_language_precision():
    valid_text = "Proficient in C, R, and Python."
    result = extract_skills(valid_text)

    assert "C" in result["languages"]
    assert "R" in result["languages"]
    assert "Python" in result["languages"]


def test_compound_and_ngram_skills():
    text = "Experience with Amazon Web Services, Spring Boot, and Google Cloud Platform."
    result = extract_skills(text)

    assert "AWS" in result["cloud_devops"]
    assert "GCP" in result["cloud_devops"]
    assert "Spring Boot" in result["frameworks_libraries"]


def test_parsing_latency_under_5ms():
    sample_skills_section = """
    Languages: Python, TypeScript, JavaScript, C++, SQL, Bash, Go, Rust
    Frontend & Backend: React.js, Next.js, Node.js, Express, FastAPI, Django
    Databases & Cloud: PostgreSQL, Redis, MongoDB, AWS, Docker, Kubernetes, Terraform
    Developer Tools: Git, GitHub Actions, Postman, Linux, Vite
    """ * 5  # Scale text to simulate long resumes

    start = time.perf_counter()
    result = extract_skills(sample_skills_section)
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 5.0, f"Extraction took {duration_ms:.2f}ms, target is < 5ms"
    assert len(result["languages"]) >= 7
    assert len(result["databases"]) >= 3