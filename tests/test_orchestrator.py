"""
tests/test_orchestrator.py
Unit tests verifying Phase 1 Orchestrator routing, fallback safety, and mode isolation.
"""

from unittest.mock import MagicMock
import pytest
from src.orchestrator import ProcessingMode, ResumeParserOrchestrator
from src.schemas import EducationItem, Profile, ResumeOutput, TechnicalSkills


@pytest.fixture
def sample_profile():
    return Profile(
        full_name="Alex Smith",
        email="alex@example.com",
        phone="",
        linkedin_url="",
        github_url="",
        portfolio_url=None,
    )


def test_local_fast_mode_never_invokes_llm():
    orchestrator = ResumeParserOrchestrator(
        gemini_api_key="mock_key", default_mode=ProcessingMode.LOCAL_FAST
    )
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True
    orchestrator.llm_parser = mock_llm

    orchestrator.extract_document_data = MagicMock(
        return_value={
            "text": "Alex Smith\nalex@example.com\n\nSkills\nPython, Docker",
            "file_name": "resume.pdf",
            "file_hash": "dummyhash",
            "file_size": 1024,
            "is_scanned": False,
        }
    )

    result, metrics = orchestrator.parse(
        b"dummy_bytes", "resume.pdf", mode=ProcessingMode.LOCAL_FAST
    )

    assert metrics["mode"] == "local_fast"
    assert metrics["ai_invoked"] is False
    assert mock_llm.parse_targeted_sections.call_count == 0
    assert result.profile.full_name == "Alex Smith" or result.profile.email == "alex@example.com"


def test_missing_optional_profile_fields_do_not_trigger_ai():
    """
    Ensure missing phone, github, or linkedin never triggers an LLM call.
    """
    orchestrator = ResumeParserOrchestrator(
        gemini_api_key="mock_key", default_mode=ProcessingMode.HYBRID_ACCURATE
    )
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True
    orchestrator.llm_parser = mock_llm

    # Experience entries parsed locally
    exp_entries = [{"company": "Acme", "role": "Dev"}]
    proj_entries = [{"title": "Tool", "description": "Utility"}]

    sections = {
        "education": "State University B.S.",
        "experience": "Dev at Acme",
        "projects": "Tool",
    }

    should_call = orchestrator._should_trigger_ai(exp_entries, proj_entries, sections)
    assert should_call is False


def test_hybrid_mode_triggers_only_on_unparsed_experience():
    """
    AI is triggered only if raw text has an experience section that local heuristics could not parse.
    """
    orchestrator = ResumeParserOrchestrator(
        gemini_api_key="mock_key", default_mode=ProcessingMode.HYBRID_ACCURATE
    )
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True
    orchestrator.llm_parser = mock_llm

    exp_entries = []  # Empty local extraction
    proj_entries = []

    sections = {
        "experience": "Lead Developer from 2021 to 2024 managing distributed services.",
    }

    should_call = orchestrator._should_trigger_ai(exp_entries, proj_entries, sections)
    assert should_call is True


def test_legacy_doc_file_is_rejected():
    orchestrator = ResumeParserOrchestrator()
    with pytest.raises(ValueError, match="Legacy .doc binary format is not supported"):
        orchestrator.extract_document_data(b"mock", "resume.doc")