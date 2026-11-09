import argparse
import json
import sys
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator import ResumeParserOrchestrator
from src.database import upload_resume_data, get_mongodb_client


def test_resume_file(file_path: str, upload_to_db: bool = False):
    orchestrator = ResumeParserOrchestrator()
    
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    print(f"Parsing: {file_path} ...")
    result = orchestrator.process_file(file_bytes, file_path)
    
    # Pretty print the final JSON
    output_json = result.model_dump_json(indent=2)
    print("\n--- Extracted JSON Output ---\n")
    print(output_json)

    # Save to disk as an artifact
    output_filename = "parsed_result.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(output_json)
    print(f"\nSaved output to {output_filename}")

    if upload_to_db:
        print("\nUploading to MongoDB...")
        try:
            db_res = upload_resume_data(result)
            print(f"Successfully uploaded to MongoDB: {db_res}")
        except Exception as e:
            print(f"Failed to upload to MongoDB: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse resume and optionally upload to MongoDB")
    parser.add_argument("file_path", help="Path to resume file (.pdf or .docx)")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload parsed resume directly to MongoDB"
    )

    args = parser.parse_args()
    test_resume_file(args.file_path, upload_to_db=args.upload)
