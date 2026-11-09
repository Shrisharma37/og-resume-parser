"""
src/database.py
MongoDB client and repository for storing parsed resume documents adhering to ResumeOutput schema.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, PyMongoError

from src.schemas import ResumeOutput

logger = logging.getLogger(__name__)

DEFAULT_DB_NAME = "resume_parser_db"
DEFAULT_COLLECTION_NAME = "resumes"


class MongoDBClient:
    """
    MongoDB manager for managing connection lifecycle and operations
    for validated resume data conforming to ResumeOutput schema.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        db_name: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.uri = uri or os.getenv("MONGODB_URI", "")
        self.db_name = db_name or os.getenv("MONGODB_DB_NAME", DEFAULT_DB_NAME)
        self.collection_name = collection_name or os.getenv(
            "MONGODB_COLLECTION_NAME", DEFAULT_COLLECTION_NAME
        )
        self._client: Optional[MongoClient] = None

    @property
    def client(self) -> MongoClient:
        """Lazy initialization of MongoClient."""
        if self._client is None:
            if not self.uri:
                raise ValueError(
                    "MONGODB_URI is not set. Please specify it in .env or pass it to MongoDBClient."
                )
            self._client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )
        return self._client

    @property
    def db(self) -> Database:
        return self.client[self.db_name]

    @property
    def collection(self) -> Collection:
        return self.db[self.collection_name]

    def ping(self) -> bool:
        """Check if connection to MongoDB is alive and responsive."""
        if not self.uri:
            return False
        try:
            self.client.admin.command("ping")
            return True
        except (ConnectionFailure, PyMongoError, Exception) as err:
            logger.warning("MongoDB ping failed: %s", err)
            return False

    def ensure_indexes(self) -> None:
        """Ensure useful search and uniqueness indexes on the collection."""
        try:
            self.collection.create_index("metadata.file_hash")
            self.collection.create_index("profile.email")
            self.collection.create_index("metadata.created_at")
        except PyMongoError as err:
            logger.warning("Failed to create indexes: %s", err)

    def upload_resume(
        self,
        resume_data: Union[ResumeOutput, Dict[str, Any]],
        upsert_by_hash: bool = True,
    ) -> Dict[str, Any]:
        """
        Validates the resume data against the ResumeOutput Pydantic schema and
        uploads it to MongoDB.

        Args:
            resume_data: Either a ResumeOutput Pydantic instance or a dictionary conforming to it.
            upsert_by_hash: If True, documents with matching metadata.file_hash will be updated.

        Returns:
            Dict containing upload status, document ID, action taken, and metadata.
        """
        # Step 1: Validate against ResumeOutput schema
        if isinstance(resume_data, ResumeOutput):
            validated_model = resume_data
        elif isinstance(resume_data, dict):
            # Strip MongoDB internal _id if present during re-validation
            data_copy = {k: v for k, v in resume_data.items() if k != "_id"}
            validated_model = ResumeOutput.model_validate(data_copy)
        else:
            raise TypeError(
                f"Expected ResumeOutput or dict, got {type(resume_data).__name__}"
            )

        # Convert to strict JSON-compatible dictionary (handles datetime / urls cleanly)
        doc: Dict[str, Any] = json.loads(validated_model.model_dump_json())
        doc["uploaded_at"] = datetime.now(timezone.utc).isoformat()

        file_hash = doc.get("metadata", {}).get("file_hash")

        # Step 2: Upload or Upsert to MongoDB
        if upsert_by_hash and file_hash:
            result = self.collection.update_one(
                {"metadata.file_hash": file_hash},
                {"$set": doc},
                upsert=True,
            )
            if result.upserted_id:
                doc_id = str(result.upserted_id)
                action = "inserted"
            else:
                existing_doc = self.collection.find_one({"metadata.file_hash": file_hash})
                doc_id = str(existing_doc["_id"]) if existing_doc else "unknown"
                action = "updated"
        else:
            insert_res = self.collection.insert_one(doc)
            doc_id = str(insert_res.inserted_id)
            action = "inserted"

        return {
            "success": True,
            "document_id": doc_id,
            "action": action,
            "file_name": doc.get("metadata", {}).get("file_name", ""),
            "file_hash": file_hash,
            "candidate_name": doc.get("profile", {}).get("full_name"),
            "candidate_email": doc.get("profile", {}).get("email"),
        }

    def get_resume(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single resume by its MongoDB ObjectId string."""
        try:
            doc = self.collection.find_one({"_id": ObjectId(document_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error("Error retrieving document %s: %s", document_id, e)
            return None

    def get_resume_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Fetch a resume by metadata.file_hash."""
        doc = self.collection.find_one({"metadata.file_hash": file_hash})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def list_resumes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent resumes from the collection."""
        cursor = self.collection.find().sort("_id", -1).limit(limit)
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    def count_resumes(self) -> int:
        """Count total resumes stored in the collection."""
        return self.collection.count_documents({})

    def delete_resume(self, document_id: str) -> bool:
        """Delete a resume by its MongoDB ObjectId."""
        try:
            res = self.collection.delete_one({"_id": ObjectId(document_id)})
            return res.deleted_count > 0
        except Exception as e:
            logger.error("Error deleting document %s: %s", document_id, e)
            return False

    def delete_resume_by_hash(self, file_hash: str) -> bool:
        """Delete a resume by its metadata.file_hash."""
        res = self.collection.delete_one({"metadata.file_hash": file_hash})
        return res.deleted_count > 0

    def close(self) -> None:
        """Close MongoDB connection pool."""
        if self._client:
            self._client.close()
            self._client = None


_global_client: Optional[MongoDBClient] = None


def get_mongodb_client() -> MongoDBClient:
    """Singleton getter for MongoDBClient."""
    global _global_client
    if _global_client is None:
        _global_client = MongoDBClient()
    return _global_client


def upload_resume_data(
    resume_data: Union[ResumeOutput, Dict[str, Any]],
    upsert_by_hash: bool = True,
) -> Dict[str, Any]:
    """Helper function to upload or update a resume in MongoDB directly."""
    client = get_mongodb_client()
    return client.upload_resume(resume_data, upsert_by_hash=upsert_by_hash)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(description="MongoDB Resume Manager CLI")
    parser.add_argument("--status", action="store_true", help="Check MongoDB connection status")
    parser.add_argument("--list", action="store_true", help="List stored resumes")
    parser.add_argument("--count", action="store_true", help="Count total resumes in database")
    parser.add_argument("--file", type=str, help="Upload a parsed JSON resume file into MongoDB")

    args = parser.parse_args()

    client = MongoDBClient()

    if args.status or len(sys.argv) == 1:
        is_ok = client.ping()
        print(f"MongoDB Ping: {'Connected (OK)' if is_ok else 'Failed'}")
        if is_ok:
            print(f"Database: {client.db_name}")
            print(f"Collection: {client.collection_name}")
            print(f"Total Resumes: {client.count_resumes()}")

    if args.count:
        print(f"Total resumes: {client.count_resumes()}")

    if args.list:
        resumes = client.list_resumes(limit=10)
        print(f"\nFound {len(resumes)} recent resume(s):")
        for idx, r in enumerate(resumes, 1):
            name = r.get("profile", {}).get("full_name") or "Unnamed"
            email = r.get("profile", {}).get("email") or "No email"
            fname = r.get("metadata", {}).get("file_name") or "N/A"
            print(f"  {idx}. ID: {r['_id']} | Name: {name} | Email: {email} | File: {fname}")

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = client.upload_resume(data)
        print(f"Uploaded successfully: {result}")
