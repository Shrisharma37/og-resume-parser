"""
upload_to_mongodb.py
CLI tool to parse and upload resumes or JSON resume documents directly to MongoDB.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.database import MongoDBClient
from src.orchestrator import ResumeParserOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Upload parsed resume data conforming to schema into MongoDB."
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to resume file (.pdf, .docx) or parsed JSON file",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check MongoDB connection status and resume count",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List recent resumes saved in MongoDB",
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Enable AI hybrid mode during file parsing",
    )

    args = parser.parse_args()
    client = MongoDBClient()

    if args.status:
        is_ok = client.ping()
        print(f"MongoDB Ping: {'Connected (OK)' if is_ok else 'Failed'}")
        if is_ok:
            print(f"Database: {client.db_name}")
            print(f"Collection: {client.collection_name}")
            print(f"Total documents: {client.count_resumes()}")
        return

    if args.list:
        resumes = client.list_resumes(limit=10)
        print(f"\n--- Resumes in MongoDB ({len(resumes)} shown) ---")
        for idx, r in enumerate(resumes, 1):
            name = r.get("profile", {}).get("full_name") or "Unnamed"
            email = r.get("profile", {}).get("email") or "No email"
            fname = r.get("metadata", {}).get("file_name") or "N/A"
            doc_id = r.get("_id")
            print(f"[{idx}] ID: {doc_id} | Candidate: {name} | Email: {email} | File: {fname}")
        return

    if not args.file:
        parser.print_help()
        sys.exit(1)

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    suffix = file_path.suffix.lower()

    if suffix == ".json":
        print(f"Reading JSON document from {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("Validating schema and uploading to MongoDB...")
        res = client.upload_resume(data)
        print(f"Successfully uploaded: {res}")

    elif suffix in (".pdf", ".docx"):
        print(f"Parsing resume document {file_path}...")
        orchestrator = ResumeParserOrchestrator()
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        parsed = orchestrator.process_file(file_bytes, file_path.name, use_ai=args.use_ai)
        print("Validating schema and uploading to MongoDB...")
        res = client.upload_resume(parsed)
        print(f"Successfully uploaded: {res}")

    else:
        print(f"Unsupported file format: {suffix}. Supported formats: .pdf, .docx, .json")
        sys.exit(1)


if __name__ == "__main__":
    main()

