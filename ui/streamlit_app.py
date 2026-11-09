import streamlit as st
import json
import os
import sys

# Ensure root directory is on the path so src imports resolve cleanly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from src.orchestrator import ResumeParserOrchestrator
from src.database import MongoDBClient, upload_resume_data

st.set_page_config(
    page_title="AI Resume Parser & MongoDB Uploader",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Hide Streamlit header (Deploy button, 3-dots menu), sidebar, and footer
st.markdown(
    """
    <style>
        /* Hide Deploy button */
        .stAppDeployButton,
        [data-testid="stAppDeployButton"] {
            display: none !important;
        }

        /* Hide 3-dots menu and header toolbar */
        #MainMenu {
            visibility: hidden !important;
            display: none !important;
        }
        header[data-testid="stHeader"] {
            visibility: hidden !important;
            height: 0% !important;
        }
        [data-testid="stToolbar"] {
            visibility: hidden !important;
            display: none !important;
        }
        [data-testid="stDecoration"] {
            display: none !important;
        }
        [data-testid="stStatusWidget"] {
            visibility: hidden !important;
            display: none !important;
        }

        /* Hide sidebar and sidebar collapse control */
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        /* Hide footer */
        footer {
            visibility: hidden !important;
            display: none !important;
        }

        /* Adjust top padding since header is hidden */
        .block-container {
            padding-top: 2rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📄 Smart AI Resume Parser")
st.caption("Upload any PDF or DOCX resume to extract structured data into standard JSON format.")

# API Key check (fallback input in expander if not found in environment)
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    with st.expander("⚙️ Gemini API Configuration", expanded=True):
        user_key = st.text_input("Enter Gemini API Key", type="password", help="Enter your Gemini API key if not configured in environment variables.")
        if user_key:
            os.environ["GEMINI_API_KEY"] = user_key
            api_key = user_key
            st.session_state.pop("orchestrator", None)
            st.rerun()

# Initialize orchestrator in session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = ResumeParserOrchestrator()

# Main tabs: Parser vs Database Explorer
nav_tab1, nav_tab2 = st.tabs(["🚀 Parse & Upload", "📚 MongoDB Resumes Browser"])

with nav_tab1:
    uploaded_file = st.file_uploader(
        "Choose a resume file",
        type=["pdf", "docx"],
        help="Supports both digital and text-extractable documents"
    )

    if uploaded_file is not None:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📎 File Details")
            st.write(f"**Filename:** `{uploaded_file.name}`")
            st.write(f"**Size:** `{uploaded_file.size / 1024:.2f} KB`")

            parse_button = st.button("🚀 Parse Resume", type="primary", use_container_width=True)

        if parse_button:
            import time
            with st.spinner("Processing document through hybrid pipeline..."):
                try:
                    start_time = time.time()
                    file_bytes = uploaded_file.getvalue()
                    result = st.session_state.orchestrator.process_file(
                        file_bytes=file_bytes,
                        filename=uploaded_file.name,
                        use_ai=True
                    )
                    elapsed = time.time() - start_time
                    st.session_state["parsed_result"] = result.model_dump()
                    st.session_state["parsed_model"] = result
                    st.success(f"Resume parsed successfully in **{elapsed:.2f}s**!")

                    # Auto-upload if enabled and MongoDB connected
                    if auto_upload and mongo_connected:
                        with st.spinner("Uploading to MongoDB..."):
                            upload_info = st.session_state.mongo_client.upload_resume(result)
                            st.session_state["last_upload"] = upload_info
                            st.toast(f"Saved to MongoDB ({upload_info['action']})", icon="✅")

                except Exception as e:
                    st.error(f"Failed to parse resume: {str(e)}")

        if "last_upload" in st.session_state and st.session_state.get("last_upload"):
            up = st.session_state["last_upload"]
            st.success(
                f"✅ **MongoDB Stored**: Document ID `{up['document_id']}` ({up['action']}) "
                f"in `{st.session_state.mongo_client.db_name}.{st.session_state.mongo_client.collection_name}`"
            )

        if "parsed_result" in st.session_state:
            data = st.session_state["parsed_result"]

            col_btn1, col_btn2 = st.columns([1, 2])
            with col_btn1:
                if mongo_connected:
                    if st.button("💾 Upload / Update in MongoDB", use_container_width=True):
                        try:
                            upload_info = st.session_state.mongo_client.upload_resume(data)
                            st.session_state["last_upload"] = upload_info
                            st.success(f"Uploaded successfully! ID: `{upload_info['document_id']}` ({upload_info['action']})")
                        except Exception as exc:
                            st.error(f"Upload failed: {exc}")

            st.divider()
            st.subheader("📋 Parsed Sections")

        tab_json, = st.tabs(["Raw JSON"])

            with tab_json:
                json_str = json.dumps(data, indent=2)
                st.json(data)
                st.download_button(
                    label="📥 Download JSON Output",
                    data=json_str,
                    file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_parsed.json",
                    mime="application/json",
                    use_container_width=True
                )

with nav_tab2:
    st.subheader("📚 Saved Resumes in MongoDB")
    if not mongo_connected:
        st.warning("MongoDB is currently disconnected. Please verify connection credentials in `.env`.")
    else:
        col_ref, _ = st.columns([1, 4])
        with col_ref:
            if st.button("🔄 Refresh Database List"):
                st.rerun()

        try:
            stored_resumes = st.session_state.mongo_client.list_resumes(limit=50)
            if not stored_resumes:
                st.info("No resumes found in the database yet. Parse and upload one above!")
            else:
                st.write(f"Showing **{len(stored_resumes)}** recent resume(s):")
                for r in stored_resumes:
                    doc_id = r.get("_id")
                    name = r.get("profile", {}).get("full_name") or "Unnamed Candidate"
                    email = r.get("profile", {}).get("email") or "No Email"
                    file_name = r.get("metadata", {}).get("file_name") or "Unknown file"
                    uploaded_at = r.get("uploaded_at") or r.get("metadata", {}).get("parsed_at", "N/A")

                    with st.expander(f"👤 **{name}** ({email}) — *{file_name}* [ID: `{doc_id}`]"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**File:** `{file_name}`")
                            st.write(f"**File Hash:** `{r.get('metadata', {}).get('file_hash', 'N/A')}`")
                            st.write(f"**Uploaded:** {uploaded_at}")
                        with c2:
                            tech_skills = r.get("technical_skills", {}).get("technologies", [])
                            st.write(f"**Skills:** {', '.join(tech_skills) if tech_skills else 'None detected'}")
                            st.write(f"**Total Projects:** {len(r.get('projects', []))}")
                            st.write(f"**Total Experience Entries:** {len(r.get('experience', []))}")

                        st.markdown("##### Complete Document JSON")
                        st.json(r)
        except Exception as e:
            st.error(f"Error loading resumes from MongoDB: {e}")
