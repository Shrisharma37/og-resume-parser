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

st.set_page_config(
    page_title="AI Resume Parser",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Smart AI Resume Parser")
st.caption("Upload any PDF or DOCX resume to extract structured data into standard JSON format.")

# Sidebar status
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        user_key = st.text_input("Enter Gemini API Key", type="password", help="Enter your Gemini API key if not configured in environment variables.")
        if user_key:
            os.environ["GEMINI_API_KEY"] = user_key
            api_key = user_key
            st.session_state.pop("orchestrator", None)

    if api_key:
        st.success("API Key detected (Hybrid Mode active)")
    else:
        st.warning("⚠️ API Key missing. Enter your Gemini API key above for full AI extraction.")

# Initialize orchestrator in session state
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = ResumeParserOrchestrator()

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
                st.success(f"Resume parsed successfully in **{elapsed:.2f}s**!")
            except Exception as e:
                st.error(f"Failed to parse resume: {str(e)}")

    if "parsed_result" in st.session_state:
        data = st.session_state["parsed_result"]

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