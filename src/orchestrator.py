"""
src/orchestrator.py
Optimized Orchestrator for Smart Resume Parser (Version 3)
Supports Local Fast Mode (<100ms) and Selective Hybrid Accuracy Mode.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.extractors.docx_extractor import extract_docx_data
from src.extractors.pdf_extractor import extract_pdf_data
from src.parsers.heuristic_parser import (
    extract_education,
    extract_experience_fallback,
    extract_list_items,
    extract_profile,
    extract_projects_fallback,
    extract_skills,
)
from src.parsers.llm_parser import ResumeLLMParser
from src.parsers.section_mapper import segment_resume_sections
from src.schemas import Metadata, ResumeOutput, TechnicalSkills

logger = logging.getLogger(__name__)


class ProcessingMode(str, Enum):
    LOCAL_FAST = "local_fast"
    HYBRID_ACCURATE = "hybrid_accurate"


class ResumeParserOrchestrator:
    """
    Coordinates document text extraction, section segmentation,
    deterministic local parsing, and targeted LLM fallbacks.
    """

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        default_mode: ProcessingMode = ProcessingMode.LOCAL_FAST,
    ) -> None:
        self.default_mode = default_mode
        self.llm_parser = ResumeLLMParser(api_key=gemini_api_key)

    def extract_document_data(
        self, file_path_or_bytes: Union[str, Path, bytes], filename: str
    ) -> Dict[str, Any]:
        """
        Routes extraction based on file extension.
        Explicitly rejects legacy binary .doc files.
        """
        ext = os.path.splitext(filename)[1].lower()

        if isinstance(file_path_or_bytes, (str, Path)):
            with open(file_path_or_bytes, "rb") as f:
                data_bytes = f.read()
        else:
            data_bytes = file_path_or_bytes

        if ext == ".pdf":
            return extract_pdf_data(data_bytes, filename)
        elif ext == ".docx":
            return extract_docx_data(data_bytes, filename)
        elif ext == ".doc":
            raise ValueError(
                "Legacy .doc binary format is not supported directly. "
                "Please convert the file to .docx or .pdf."
            )
        else:
            raise ValueError(f"Unsupported document format: {ext}")

    def _should_trigger_ai(
        self,
        exp_entries: list,
        proj_entries: list,
        sections: Dict[str, str],
    ) -> bool:
        """
        Determines whether Gemini needs to be invoked in Hybrid Mode.
        Deterministic fields (name, email, phone, links, location, skills, education)
        DO NOT trigger AI calls, even when optional fields are empty.

        AI is only triggered when unstructured narrative sections (experience/projects)
        are present in raw text but could not be parsed into structured objects by heuristics.
        """
        if not self.llm_parser or not self.llm_parser.is_available():
            return False

        has_experience_text = bool(sections.get("experience", "").strip())
        has_projects_text = bool(sections.get("projects", "").strip())

        unresolved_experience = has_experience_text and len(exp_entries) == 0
        unresolved_projects = has_projects_text and len(proj_entries) == 0

        return unresolved_experience or unresolved_projects

    def parse(
        self,
        file_path_or_bytes: Union[str, Path, bytes],
        filename: str,
        mode: Optional[ProcessingMode] = None,
    ) -> Tuple[ResumeOutput, Dict[str, Any]]:
        """
        Main orchestration entry point returning structured ResumeOutput and performance metrics.
        """
        start_time = time.perf_counter()
        active_mode = mode or self.default_mode
        metrics: Dict[str, Any] = {
            "mode": active_mode.value,
            "ai_invoked": False,
            "timings_ms": {},
        }

        # Step 1: Text extraction
        t0 = time.perf_counter()
        extracted = self.extract_document_data(file_path_or_bytes, filename)
        raw_text = extracted.get("text", "")
        metrics["timings_ms"]["text_extraction"] = round((time.perf_counter() - t0) * 1000, 2)

        if not raw_text.strip():
            raise ValueError("The uploaded document contains no readable text.")

        # Step 2: Deterministic Section Segmentation (<2ms)
        t1 = time.perf_counter()
        sections = segment_resume_sections(raw_text)
        metrics["timings_ms"]["section_mapping"] = round((time.perf_counter() - t1) * 1000, 2)

        # Step 3: Deterministic Local Heuristic Extraction (<2ms)
        t2 = time.perf_counter()
        profile_text = sections.get("profile", "")
        header_text = (
            profile_text
            if len(profile_text.splitlines()) >= 5
            else "\n".join(raw_text.splitlines()[:25])
        )
        profile = extract_profile(raw_text, header_text)

        skills_text = sections.get("technical_skills", "")
        skills_list = extract_skills(skills_text)
        technical_skills = TechnicalSkills(technologies=skills_list)

        education_text = sections.get("education", "")
        education = extract_education(education_text)

        certifications = extract_list_items(sections.get("certifications", ""))
        achievements = extract_list_items(sections.get("achievements", ""))

        exp_text = sections.get("experience", "")
        proj_text = sections.get("projects", "")

        experience = extract_experience_fallback(exp_text)
        projects = extract_projects_fallback(proj_text)
        metrics["timings_ms"]["heuristic_parsing"] = round((time.perf_counter() - t2) * 1000, 2)

        # Step 4: Hybrid Targeted Fallback (Only in HYBRID_ACCURATE mode)
        ai_called = False
        if active_mode == ProcessingMode.HYBRID_ACCURATE:
            if self._should_trigger_ai(experience, projects, sections):
                t_ai = time.perf_counter()
                try:
                    targeted_payload = {
                        "experience_text": exp_text,
                        "projects_text": proj_text,
                        "summary_text": sections.get("summary", ""),
                    }
                    ai_result = self.llm_parser.parse_targeted_sections(targeted_payload)
                    if ai_result.get("experience"):
                        experience = ai_result["experience"]
                    if ai_result.get("projects"):
                        projects = ai_result["projects"]
                    ai_called = True
                    metrics["ai_invoked"] = True
                except Exception as exc:
                    logger.warning("Targeted AI fallback failed: %s. Preserving local extraction.", exc)
                    metrics["ai_error"] = str(exc)
                finally:
                    metrics["timings_ms"]["ai_invocation"] = round(
                        (time.perf_counter() - t_ai) * 1000, 2
                    )

        # Step 5: Assemble Metadata
        timestamp_str = datetime.now(timezone.utc).isoformat()
        metadata = Metadata(
            parser_version="3.0-hybrid",
            status="completed",
            created_at=timestamp_str,
            parsed_at=timestamp_str,
            file_name=extracted["file_name"],
            file_hash=extracted["file_hash"],
            file_size_bytes=extracted["file_size"],
            ai_called_for_projects_or_experience=ai_called,
            is_scanned_pdf=extracted.get("is_scanned", False),
        )

        metrics["timings_ms"]["total"] = round((time.perf_counter() - start_time) * 1000, 2)

        output = ResumeOutput(
            profile=profile,
            education=education,
            technical_skills=technical_skills,
            projects=projects,
            experience=experience,
            certifications=certifications,
            achievements=achievements,
            metadata=metadata,
        )
        return output, metrics

    def process_file(
        self, file_bytes: bytes, filename: str, use_ai: bool = False
    ) -> ResumeOutput:
        """Backward compatibility wrapper for existing callers."""
        mode = ProcessingMode.HYBRID_ACCURATE if use_ai else ProcessingMode.LOCAL_FAST
        output, _ = self.parse(file_bytes, filename, mode=mode)
        return output


ResumeOrchestrator = ResumeParserOrchestrator