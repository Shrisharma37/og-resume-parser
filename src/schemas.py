from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field, HttpUrl, model_validator


class Profile(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None

class EducationItem(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    grade_or_gpa: Optional[str] = None

class TechnicalSkills(BaseModel):
    technologies: List[str] = Field(default_factory=list)

class Project(BaseModel):
    title: str = "Untitled Project"
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    link: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "title" not in data and "name" in data:
                data["title"] = data.get("name") or "Untitled Project"
            elif "title" in data and not data["title"] and data.get("name"):
                data["title"] = data["name"]
            if isinstance(data.get("description"), list):
                data["description"] = "\n".join(data["description"])
            return data
        elif hasattr(data, "model_dump") or hasattr(data, "__dict__"):
            dump = data.model_dump() if hasattr(data, "model_dump") else getattr(data, "__dict__", {})
            title = dump.get("title") or dump.get("name") or "Untitled Project"
            desc = dump.get("description")
            if not desc and dump.get("highlights"):
                desc = "\n".join(dump["highlights"])
            elif isinstance(desc, list):
                desc = "\n".join(desc)
            return {
                "title": title,
                "name": dump.get("name") or title,
                "role": dump.get("role"),
                "description": desc,
                "technologies": dump.get("technologies") or [],
                "link": dump.get("link"),
            }
        return data

class Experience(BaseModel):
    company: str = "Unknown Company"
    role: Optional[str] = None
    experience_type: Optional[str] = "full_time"  # internship, volunteer, other, etc.
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "role" not in data and "title" in data:
                data["role"] = data.get("title")
            if not data.get("company"):
                data["company"] = "Unknown Company"
            if isinstance(data.get("description"), list):
                data["description"] = "\n".join(data["description"])
            return data
        elif hasattr(data, "model_dump") or hasattr(data, "__dict__"):
            dump = data.model_dump() if hasattr(data, "model_dump") else getattr(data, "__dict__", {})
            desc = dump.get("description")
            if not desc and dump.get("highlights"):
                desc = "\n".join(dump["highlights"])
            elif isinstance(desc, list):
                desc = "\n".join(desc)
            return {
                "company": dump.get("company") or "Unknown Company",
                "role": dump.get("role") or dump.get("title"),
                "experience_type": dump.get("experience_type", "full_time"),
                "start_date": dump.get("start_date"),
                "end_date": dump.get("end_date"),
                "description": desc,
                "technologies": dump.get("technologies") or [],
            }
        return data

class Metadata(BaseModel):
    parser_version: str = "1.0"
    status: str = "completed"
    created_at: str
    parsed_at: str
    file_name: str
    file_hash: str
    file_size_bytes: int
    ai_called_for_projects_or_experience: bool = True
    is_scanned_pdf: bool = False

class ResumeOutput(BaseModel):
    profile: Profile
    education: List[EducationItem] = Field(default_factory=list)
    technical_skills: TechnicalSkills
    projects: List[Project] = Field(default_factory=list)
    experience: List[Experience] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    metadata: Metadata