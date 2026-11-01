import os
from datetime import datetime, timezone
from typing import Optional, List

from src.extractors.pdf_extractor import extract_pdf_data
from src.extractors.docx_extractor import extract_docx_data
from src.parsers.section_mapper import segment_resume_sections
from src.parsers.heuristic_parser import (
    extract_profile,
    extract_skills,
    extract_education,
    extract_list_items,
    extract_projects_fallback,
    extract_experience_fallback
)
from src.parsers.llm_parser import ResumeLLMParser
from src.schemas import ResumeOutput, TechnicalSkills, Metadata


class ResumeParserOrchestrator:
    def __init__(self, api_key: Optional[str] = None):
        self.llm_parser = ResumeLLMParser(api_key=api_key)

    def process_file(
        self, file_bytes: bytes, filename: str, use_ai: bool = True
    ) -> ResumeOutput:
        """
        Processes a resume file through the Hybrid Parsing Pipeline:
        1. Fast local text & hyperlink extraction (PDF / DOCX)
        2. Fast deterministic section segmentation
        3. Local heuristic extraction for Profile, Skills, Education, Certifications, Achievements
        4. Targeted Gemini AI extraction for Projects, Experience, and missing Profile fields (LinkedIn, GitHub, Summary)
        """
        ext = os.path.splitext(filename)[1].lower()
        
        if ext == ".pdf":
            extracted = extract_pdf_data(file_bytes, filename)
        elif ext in [".docx", ".doc"]:
            extracted = extract_docx_data(file_bytes, filename)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Only .pdf and .docx are supported.")

        raw_text = extracted["text"]
        if not raw_text.strip():
            raise ValueError("The uploaded document contains no readable text. It may be an image-only scan.")

        # 1. Deterministic Section Segmentation (Instant, <2ms)
        sections = segment_resume_sections(raw_text)

        # 2. Extract Profile deterministically (Regex & rules, <1ms)
        profile_text = sections.get("profile", "")
        # If profile section is short, also include the top 25 lines of raw text for context
        header_text = profile_text if len(profile_text.splitlines()) >= 5 else "\n".join(raw_text.splitlines()[:25])
        profile = extract_profile(raw_text, header_text)

        # 3. Extract Technical Skills strictly from designated section (Strict isolation rule)
        skills_text = sections.get("technical_skills", "")
        skills_list = extract_skills(skills_text)
        technical_skills = TechnicalSkills(technologies=skills_list)

        # 4. Extract Education deterministically
        education_text = sections.get("education", "")
        education = extract_education(education_text)

        # 5. Extract Certifications and Achievements
        certifications = extract_list_items(sections.get("certifications", ""))
        achievements = extract_list_items(sections.get("achievements", ""))

        # 6. Check for missing profile attributes that AI should enrich
        missing_profile_fields: List[str] = []
        if not profile.linkedin_url:
            missing_profile_fields.append("linkedin_url")
        if not profile.github_url:
            missing_profile_fields.append("github_url")
        if not profile.summary:
            missing_profile_fields.append("summary")
        if not profile.portfolio_url:
            missing_profile_fields.append("portfolio_url")
        if not profile.full_name:
            missing_profile_fields.append("full_name")
        if not profile.location:
            missing_profile_fields.append("location")
        if not profile.phone:
            missing_profile_fields.append("phone")

        # 7. Extract Experience, Projects & enrich Profile (Targeted Gemini Hybrid Call)
        exp_text = sections.get("experience", "")
        proj_text = sections.get("projects", "")
        ai_called = False

        experience = []
        projects = []

        should_call_ai = use_ai and self.llm_parser.is_available() and (
            exp_text.strip() or proj_text.strip() or missing_profile_fields
        )

        if should_call_ai:
            try:
                ai_output = self.llm_parser.parse_hybrid_entities(
                    profile_text=header_text,
                    experience_text=exp_text,
                    projects_text=proj_text,
                    missing_profile_fields=missing_profile_fields
                )
                ai_called = True
                
                # Enrich missing profile fields from AI
                if not profile.linkedin_url and ai_output.linkedin_url:
                    profile.linkedin_url = ai_output.linkedin_url
                if not profile.github_url and ai_output.github_url:
                    profile.github_url = ai_output.github_url
                if not profile.summary and ai_output.summary:
                    profile.summary = ai_output.summary
                if not profile.portfolio_url and ai_output.portfolio_url:
                    profile.portfolio_url = ai_output.portfolio_url
                if not profile.full_name and ai_output.full_name:
                    profile.full_name = ai_output.full_name
                if not profile.location and ai_output.location:
                    profile.location = ai_output.location
                if not profile.phone and ai_output.phone:
                    profile.phone = ai_output.phone

                experience = ai_output.experience
                projects = ai_output.projects

            except Exception as e:
                print(f"Warning: Targeted Gemini extraction failed ({e}), using heuristic fallback.")
                experience = extract_experience_fallback(exp_text)
                projects = extract_projects_fallback(proj_text)
        else:
            experience = extract_experience_fallback(exp_text)
            projects = extract_projects_fallback(proj_text)

        # 8. Assemble Metadata
        timestamp_str = datetime.now(timezone.utc).isoformat()
        metadata = Metadata(
            parser_version="2.0-hybrid",
            status="completed",
            created_at=timestamp_str,
            parsed_at=timestamp_str,
            file_name=extracted["file_name"],
            file_hash=extracted["file_hash"],
            file_size_bytes=extracted["file_size"],
            ai_called_for_projects_or_experience=ai_called,
            is_scanned_pdf=extracted.get("is_scanned", False)
        )

        return ResumeOutput(
            profile=profile,
            education=education,
            technical_skills=technical_skills,
            projects=projects,
            experience=experience,
            certifications=certifications,
            achievements=achievements,
            metadata=metadata
        )