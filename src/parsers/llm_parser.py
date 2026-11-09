import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.schemas import Experience, Project, ResumeOutput

logger = logging.getLogger(__name__)

load_dotenv(override=True)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False


class HybridAIOutput(BaseModel):
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    full_name: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)


class ResumeLLMParser:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if GENAI_AVAILABLE and self.api_key and genai:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
        self.model_name = "gemini-2.5-flash"

    def is_available(self) -> bool:
        return self.client is not None

    def parse_hybrid_entities(
        self,
        profile_text: str,
        experience_text: str,
        projects_text: str,
        missing_profile_fields: Optional[List[str]] = None,
    ) -> HybridAIOutput:
        """
        Targeted Hybrid AI Call:
        Extracts unstructured Experience & Projects, and resolves missing profile fields
        from the profile header text.
        """
        if not self.client:
            raise ValueError("Gemini client is not initialized. Please provide a GEMINI_API_KEY.")

        fields_guidance = ""
        if missing_profile_fields:
            fields_guidance = (
                f"CRITICAL: Look carefully in the Profile Header text to extract "
                f"these missing fields: {', '.join(missing_profile_fields)}."
            )

        prompt = f"""You are a high-speed resume entity extraction engine.
Extract structured entities strictly from the provided text blocks below.
{fields_guidance}

Extraction Schema:
- linkedin_url: Candidate's LinkedIn profile full URL (e.g. https://linkedin.com/in/...). If only username is written, convert to full URL.
- github_url: Candidate's GitHub profile full URL (e.g. https://github.com/...). If only username is written, convert to full URL.
- portfolio_url: Candidate's personal portfolio or website URL
- summary: Professional bio, career objective, or summary paragraph
- full_name: Candidate's full name
- location: Candidate's location (City, State, Country)
- phone: Candidate's phone number if and ONLY if explicitly written in the header. If no phone number is provided, return null. Do NOT extract roll numbers, dates, or other numbers as a phone number.
- projects: list of {{ title, role, description, technologies: [] }}
- experience: list of {{ company, role, experience_type, start_date, end_date, description, technologies: [] }}

--- Profile Header Text ---
{profile_text}

--- Projects Text ---
{projects_text}

--- Experience Text ---
{experience_text}
"""

        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=HybridAIOutput,
                        temperature=0.1,
                    ),
                )
                return HybridAIOutput.model_validate_json(response.text)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1.5)
                else:
                    raise e

    def parse_experience_and_projects(
        self, experience_text: str, projects_text: str
    ) -> Tuple[List[Experience], List[Project]]:
        result = self.parse_hybrid_entities("", experience_text, projects_text)
        return result.experience, result.projects

    def parse_resume_full(self, resume_text: str, metadata_defaults: dict) -> ResumeOutput:
        if not self.client:
            raise ValueError("Gemini client is not initialized. Please provide a GEMINI_API_KEY.")

        prompt = f"""You are an expert resume parsing engine.
Analyze the raw resume text below and extract all entities strictly into the specified JSON format.

JSON Schema requirements:
- profile: {{ full_name, email, phone, location, linkedin_url, github_url, portfolio_url, summary }}
- education: list of {{ institution, degree, field_of_study, start_date, end_date, grade_or_gpa }}
- technical_skills: {{ technologies: [] }}
- projects: list of {{ title, role, description, technologies: [] }}
- experience: list of {{ company, role, experience_type, start_date, end_date, description, technologies: [] }}
- certifications: []
- achievements: []
- metadata:
    parser_version: "1.0"
    status: "completed"
    created_at: "{metadata_defaults.get('timestamp')}"
    parsed_at: "{metadata_defaults.get('timestamp')}"
    file_name: "{metadata_defaults.get('file_name')}"
    file_hash: "{metadata_defaults.get('file_hash')}"
    file_size_bytes: {metadata_defaults.get('file_size_bytes')}
    ai_called_for_projects_or_experience: true
    is_scanned_pdf: {str(metadata_defaults.get('is_scanned', False)).lower()}

--- Resume Raw Text ---
{resume_text}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ResumeOutput,
                temperature=0.1,
            ),
        )

        return ResumeOutput.model_validate_json(response.text)

    def parse_targeted_sections(self, targeted_payload: Dict[str, str]) -> Dict[str, Any]:
        if not self.client:
            return {}

        prompt = f"""You are an expert resume parsing engine. Extract structured data ONLY from the text provided below.
Return a valid JSON object matching this schema:
{{
  "summary": "string or null",
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "location": "City, Country or null",
      "start_date": "YYYY or Month YYYY or null",
      "end_date": "YYYY or Present or null",
      "description": ["bullet point 1", "bullet point 2"]
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Project overview",
      "technologies": ["tech1", "tech2"],
      "link": "url or null"
    }}
  ]
}}

--- Experience Text ---
{targeted_payload.get('experience_text', '')}

--- Projects Text ---
{targeted_payload.get('projects_text', '')}

--- Summary Text ---
{targeted_payload.get('summary_text', '')}

Only return pure JSON. Do not fabricate or invent facts not present in the text.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error in parse_targeted_sections: {e}")
            return {}