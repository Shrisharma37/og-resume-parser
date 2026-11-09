"""
tests/test_database.py
Unit tests verifying MongoDB client schema validation, upsert logic, and serialization.
"""

from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError

from src.database import MongoDBClient
from src.schemas import Metadata, Profile, ResumeOutput, TechnicalSkills


@pytest.fixture
def mock_resume_output():
    return ResumeOutput(
        profile=Profile(
            full_name="Jane Doe",
            email="jane.doe@example.com",
            phone="+1234567890",
            location="New York, NY",
            linkedin_url="https://linkedin.com/in/janedoe",
            github_url="https://github.com/janedoe",
            summary="Passionate software developer.",
        ),
        education=[],
        technical_skills=TechnicalSkills(technologies=["Python", "MongoDB", "pytest"]),
        projects=[],
        experience=[],
        certifications=[],
        achievements=[],
        metadata=Metadata(
            parser_version="3.0-hybrid",
            status="completed",
            created_at="2026-11-09T00:00:00Z",
            parsed_at="2026-11-09T00:00:00Z",
            file_name="jane_resume.pdf",
            file_hash="mock_hash_12345",
            file_size_bytes=2048,
            ai_called_for_projects_or_experience=False,
            is_scanned_pdf=False,
        ),
    )


def test_invalid_schema_rejected():
    """Attempting to upload data that does not conform to ResumeOutput schema must raise ValidationError."""
    client = MongoDBClient(uri="mongodb://localhost:27017")
    client._client = MagicMock()

    invalid_data = {
        "candidate": "Jane Doe",
        # Missing required schema structures: profile, technical_skills, metadata
    }

    with pytest.raises(ValidationError):
        client.upload_resume(invalid_data)


def test_upload_resume_with_model_inserts_successfully(mock_resume_output):
    """Verify that uploading a ResumeOutput instance performs upsert and sets document fields."""
    client = MongoDBClient(uri="mongodb://localhost:27017")
    mock_mongo = MagicMock()
    mock_coll = MagicMock()

    # Mock update_one to simulate insertion
    mock_update_result = MagicMock()
    mock_update_result.upserted_id = "mock_obj_id_999"
    mock_coll.update_one.return_value = mock_update_result

    mock_mongo.__getitem__.return_value.__getitem__.return_value = mock_coll
    client._client = mock_mongo

    result = client.upload_resume(mock_resume_output, upsert_by_hash=True)

    assert result["success"] is True
    assert result["document_id"] == "mock_obj_id_999"
    assert result["action"] == "inserted"
    assert result["file_hash"] == "mock_hash_12345"
    assert result["candidate_name"] == "Jane Doe"
    assert result["candidate_email"] == "jane.doe@example.com"
    mock_coll.update_one.assert_called_once()


def test_upload_resume_with_dict_validates_and_upserts(mock_resume_output):
    """Verify that uploading a conforming dict validates successfully and performs update."""
    client = MongoDBClient(uri="mongodb://localhost:27017")
    mock_mongo = MagicMock()
    mock_coll = MagicMock()

    # Mock update_one when document already existed
    mock_update_result = MagicMock()
    mock_update_result.upserted_id = None
    mock_coll.update_one.return_value = mock_update_result
    mock_coll.find_one.return_value = {"_id": "existing_id_888"}

    mock_mongo.__getitem__.return_value.__getitem__.return_value = mock_coll
    client._client = mock_mongo

    raw_dict = mock_resume_output.model_dump()
    result = client.upload_resume(raw_dict, upsert_by_hash=True)

    assert result["success"] is True
    assert result["document_id"] == "existing_id_888"
    assert result["action"] == "updated"


def test_ensure_indexes(mock_resume_output):
    """Verify index creation logic."""
    client = MongoDBClient(uri="mongodb://localhost:27017")
    mock_mongo = MagicMock()
    mock_coll = MagicMock()
    mock_mongo.__getitem__.return_value.__getitem__.return_value = mock_coll
    client._client = mock_mongo

    client.ensure_indexes()
    assert mock_coll.create_index.call_count == 3

