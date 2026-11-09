# 📄 Smart AI Resume Parser

An intelligent, high-speed **Hybrid Resume Parsing Engine** that ingests unstructured PDF and DOCX documents, segments career sections, and outputs a strictly validated JSON structure conforming to standard schemas. 

Built using Python, Streamlit, Google GenAI (`gemini-2.5-flash`), `pdfplumber`, `python-docx`, and Pydantic v2.

---

## ⚡ Architecture: The Hybrid Advantage

Rather than sending entire 3-page resumes to an LLM in a single slow, expensive monolithic call (which takes 12–15+ seconds), this system uses a **Hybrid Multi-Stage Pipeline**:

```text
                             Uploaded Resume (.pdf / .docx)
                                           │
                        [ Fast Local Text & Link Extraction ]
                                           │
         ┌─────────────────────────────────┴─────────────────────────────────┐
         ▼                                                                   ▼
[ Local Heuristics (<10ms) ]                                [ Section Segmenter (<2ms) ]
• Email, Phone, URLs (Regex)                                • Section header normalization
• Candidate Name (Header lines)                             • Canonical synonym matching
• Education, Certifications, Achievements                   • Strict skills isolation
• Embedded Hyperlink parsing (PDF & DOCX)
         │                                                                   │
         └─────────────────────────────────┬─────────────────────────────────┘
                                           ▼
                       ┌───────────────────────────────────────┐
                       │       Targeted Gemini AI (~2s)        │
                       │ • Structured Projects & Experience    │
                       │ • Enriches missing profile fields     │
                       │   (LinkedIn, GitHub, Summary)         │
                       │ • Graceful fallback if offline/no key │
                       └───────────────────────────────────────┘
                                           │
                                           ▼
                                 Validated ResumeOutput JSON
```

- **Blazing Fast**: Completes in **~2 seconds** (over 5x faster than pure LLM parsers).
- **Embedded Link Recovery**: Extracts hyperlinks attached to icons (e.g. SVG badges for GitHub/LinkedIn) in both PDF and DOCX files.
- **Strict Skill Isolation**: Technologies in `technical_skills.technologies` originate strictly from designated skills sections and are never mixed with project or work experience tools.
- **Resilient Offline Fallback**: If the Gemini API is temporarily unavailable or an API key is not configured, the engine falls back to local heuristic extraction so processing never halts.

---

## 📂 Project Hierarchy

```text
resume-parser/
│
├── .env                          # API key configuration (local)
├── .gitignore                    # Standard Python, environment, and cache exclusions
├── requirements.txt              # Core project dependencies
├── runtime.txt                   # Render Python runtime specification (python-3.11.9)
├── test_backend.py               # CLI test script for pipeline verification
│
├── src/
│   ├── __init__.py
│   ├── schemas.py                # Pydantic v2 resume schema definition
│   ├── orchestrator.py           # Pipeline controller (routing, hashing, parsing)
│   │
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py      # PDF text & embedded link extraction
│   │   └── docx_extractor.py     # DOCX paragraphs, tables & relationship links
│   │
│   └── parsers/
│       ├── __init__.py
│       ├── section_mapper.py     # Deterministic section header matching & segmentation
│       ├── heuristic_parser.py   # Regex & rules for profile, skills, education, list items
│       └── llm_parser.py         # Targeted Google GenAI structured JSON parser
│
└── ui/
    ├── __init__.py
    └── streamlit_app.py          # Interactive Streamlit dashboard
```

---

## 📋 JSON Output Structure

The output strictly follows this validated schema:

```json
{
  "profile": {
    "full_name": "Vivek Awasthi",
    "email": "vivekawasthi2007@gmail.com",
    "phone": "+91 8516803872",
    "location": "Chhatarpur, Madhya Pradesh",
    "linkedin_url": "https://linkedin.com/in/vivek-awasthi-33656a329",
    "github_url": "https://github.com/vivekawasthi2007",
    "portfolio_url": null,
    "summary": "Dynamic software engineer with experience developing full-stack web applications and AI pipelines."
  },
  "education": [
    {
      "institution": "LNCT Group of Colleges, Bhopal",
      "degree": "Bachelor of Technology in Computer Science",
      "field_of_study": null,
      "start_date": "2020",
      "end_date": "2024",
      "grade_or_gpa": "8.5/10"
    }
  ],
  "technical_skills": {
    "technologies": ["Python", "Django", "JavaScript", "React", "SQLite", "PostgreSQL", "Docker"]
  },
  "projects": [
    {
      "title": "Airlines Management System",
      "role": "Full Stack Developer",
      "description": "Salesforce-based system managing flight bookings, passenger records, and airline operations.",
      "technologies": ["Salesforce", "Apex", "Python", "Django", "Tailwind CSS"]
    }
  ],
  "experience": [
    {
      "company": "LNCT Group of Colleges",
      "role": "Volunteer - Training & Placement (T&P) Department",
      "experience_type": "volunteer",
      "start_date": "2023",
      "end_date": "2024",
      "description": "Assisted with placement drives and coordinated with recruiters.",
      "technologies": []
    }
  ],
  "certifications": [
    "AWS Certified Cloud Practitioner",
    "Python for Everybody (Coursera)"
  ],
  "achievements": [
    "Winner of National Level Hackathon 2023",
    "5-star rating in Python on HackerRank"
  ],
  "metadata": {
    "parser_version": "2.0-hybrid",
    "status": "completed",
    "created_at": "2026-11-01T10:00:00.000000+00:00",
    "parsed_at": "2026-11-01T10:00:00.000000+00:00",
    "file_name": "resume.pdf",
    "file_hash": "182301160d61f331e1abbe80bde16b6a874a77de917c7e9f2f31272c5d36697a",
    "file_size_bytes": 135772,
    "ai_called_for_projects_or_experience": true,
    "is_scanned_pdf": false
  }
}
```

---

## ⚙️ Local Installation & Setup

### 1. Virtual Environment Setup

```powershell
# Clone or navigate to the repository
cd resume-parser

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here

# MongoDB Configuration
MONGODB_URI=mongodb+srv://<db_username>:<db_password>@parsercluster.pbr6nkx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB_NAME=resume_parser_db
MONGODB_COLLECTION_NAME=resumes
```

*(Note: If no Gemini API key is provided, the parser runs in offline heuristic mode).*

---

## 💻 Running the Application

### Option 1: Run the Streamlit Web Interface
```powershell
streamlit run ui/streamlit_app.py
```
Open `http://localhost:8501` in your browser. Drag and drop any `.pdf` or `.docx` resume to inspect structured sections and download the JSON.

### Option 2: Run CLI Backend Verification & MongoDB Upload
```powershell
# Parse resume and print formatted JSON
python test_backend.py "path\to\resume.pdf"

# Parse resume and upload directly to MongoDB
python test_backend.py "path\to\resume.pdf" --upload

# Or use the MongoDB utility tool
python upload_to_mongodb.py --status
python upload_to_mongodb.py --list
python upload_to_mongodb.py "path\to\resume.pdf"
```

---

## ☁️ Deployment Guide (Render)

When deploying as a **Web Service** on [Render](https://render.com):

1. **Environment**: `Python`
2. **Build Command**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Start Command**:
   ```bash
   streamlit run ui/streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
   ```
4. **Environment Variables**:
   * `GEMINI_API_KEY`: *Your Google Gemini API Key*
   * `PYTHON_VERSION`: `3.11.9` *(automatically respected via `runtime.txt`)*
