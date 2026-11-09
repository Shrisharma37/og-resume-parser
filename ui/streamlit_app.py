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
    layout="wide"
)

st.title("📄 Smart AI Resume Parser & MongoDB Storage")
st.caption("Upload PDF or DOCX resumes to extract structured data and store them in MongoDB conforming to standard schemas.")

# Initialize MongoDB client in session state
if "mongo_client" not in st.session_state:
    st.session_state.mongo_client = MongoDBClient()

# Check MongoDB connectivity
mongo_connected = False
try:
    mongo_connected = st.session_state.mongo_client.ping()
except Exception:
    mongo_connected = False

# Sidebar status & Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Gemini API Key
    st.subheader("🤖 AI Extractor")
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        user_key = st.text_input(
            "Enter Gemini API Key",
            type="password",
            help="Enter your Gemini API key if not configured in environment variables."
        )
        if user_key:
            os.environ["GEMINI_API_KEY"] = user_key
            api_key = user_key
            st.session_state.pop("orchestrator", None)

    if api_key:
        st.success("API Key detected (Hybrid Mode active)")
    else:
        st.info("ℹ️ Local Heuristics active (Offline Mode)")

    st.divider()

    # MongoDB Status
    st.subheader("🍃 MongoDB Storage")
    if mongo_connected:
        st.success(f"Connected to `{st.session_state.mongo_client.db_name}`")
        st.caption(f"Collection: `{st.session_state.mongo_client.collection_name}`")
        try:
            total_docs = st.session_state.mongo_client.count_resumes()
            st.metric(label="Total Saved Resumes", value=total_docs)
        except Exception:
            pass
    else:
        st.error("MongoDB not connected. Check MONGODB_URI in `.env`.")

    auto_upload = st.checkbox(
        "Auto-upload to MongoDB upon parsing",
        value=True,
        disabled=not mongo_connected,
        help="Automatically validates schema and saves parsed resumes to MongoDB"
    )

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

            tab_preview, tab_json = st.tabs(["Structured View", "Raw JSON"])

            with tab_preview:
                # Candidate Profile Summary
                profile = data.get("profile", {})
                st.markdown(f"### {profile.get('full_name') or 'Candidate Profile'}")
                
                p_cols = st.columns(5)
                p_cols[0].markdown(f"**Email:** {profile.get('email') or '—'}")
                p_cols[1].markdown(f"**Phone:** {profile.get('phone') or '—'}")
                p_cols[2].markdown(f"**Location:** {profile.get('location') or '—'}")
                
                linkedin_url = profile.get("linkedin_url")
                linkedin_display = f"[LinkedIn]({linkedin_url})" if linkedin_url else "—"
                p_cols[3].markdown(f"**LinkedIn:** {linkedin_display}")

                github_url = profile.get("github_url")
                github_display = f"[GitHub]({github_url})" if github_url else "—"
                p_cols[4].markdown(f"**GitHub:** {github_display}")

                if profile.get("portfolio_url"):
                    st.markdown(f"**Portfolio / Website:** [{profile.get('portfolio_url')}]({profile.get('portfolio_url')})")

                if profile.get("summary"):
                    st.info(f"**Summary:** {profile.get('summary')}")
                
                # Technical Skills
                st.markdown("#### 🛠️ Technical Skills")
                skills = data.get("technical_skills", {}).get("technologies", [])
                if skills:
                    st.write(", ".join([f"`{skill}`" for skill in skills]))
                else:
                    st.caption("No technical skills detected.")

                # Projects
                st.markdown("#### 📂 Projects")
                projects = data.get("projects", [])
                if projects:
                    for proj in projects:
                        with st.expander(f"**{proj.get('title')}** ({proj.get('role') or 'Developer'})"):
                            st.write(proj.get("description") or "No description provided.")
                            if proj.get("technologies"):
                                st.caption(f"Tech: {', '.join(proj.get('technologies'))}")
                else:
                    st.caption("No projects detected.")

                # Experience
                st.markdown("#### 💼 Experience")
                experiences = data.get("experience", [])
                if experiences:
                    for exp in experiences:
                        with st.expander(f"**{exp.get('role')}** at {exp.get('company')}"):
                            st.caption(f"Dates: {exp.get('start_date') or 'N/A'} - {exp.get('end_date') or 'N/A'} ({exp.get('experience_type')})")
                            st.write(exp.get("description") or "")
                else:
                    st.caption("No experience records detected.")

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
