import streamlit as st
import json
import io
from resume_processor import ResumeProcessor
from gemini_client import GeminiClient

st.set_page_config(
    page_title="Resume Tailor AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("Resume Tailor AI")
st.caption("ATS-Optimized · Format-Safe · Gemini-Powered")

# Load API key securely from Streamlit secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("GEMINI_API_KEY not found in Streamlit secrets.")
    st.stop()

client = GeminiClient(GEMINI_API_KEY)

# Session state
if "resume_processor" not in st.session_state:
    st.session_state.resume_processor = None
if "ats_analysis" not in st.session_state:
    st.session_state.ats_analysis = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []
if "choices_made" not in st.session_state:
    st.session_state.choices_made = {}

uploaded_file = st.file_uploader("Upload your resume (.docx only)", type=["docx"])
job_description = st.text_area("Paste Job Description", height=250)

if uploaded_file:
    file_bytes = uploaded_file.read()
    st.session_state.resume_processor = ResumeProcessor(file_bytes)
    st.success("Resume uploaded successfully.")

if st.session_state.resume_processor:
    with st.expander("Preview extracted resume lines"):
        lines = st.session_state.resume_processor.get_all_lines()
        for line in lines:
            if line["text"].strip():
                st.write(f'[{line["index"]}] ({line["char_count"]} chars) {line["text"]}')

if st.button("Analyze ATS Match"):
    if not st.session_state.resume_processor:
        st.warning("Please upload a resume first.")
    elif not job_description.strip():
        st.warning("Please paste the job description.")
    else:
        resume_text = "\n".join(
            [
                line["text"]
                for line in st.session_state.resume_processor.get_all_lines()
                if line["text"].strip()
            ]
        )

        with st.spinner("Analyzing ATS match..."):
            ats_analysis = client.analyze_ats(resume_text, job_description)
            st.session_state.ats_analysis = ats_analysis

        st.success("ATS analysis complete.")

if st.session_state.ats_analysis:
    ats = st.session_state.ats_analysis

    st.subheader("ATS Analysis")
    st.metric("ATS Score", f'{ats.get("ats_score", 0)}%')
    st.write(ats.get("score_note", ""))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Present Keywords")
        for kw in ats.get("present_keywords", []):
            st.markdown(f"- {kw}")

    with col2:
        st.markdown("### Missing Keywords")
        for kw in ats.get("missing_keywords", []):
            st.markdown(f"- {kw}")

    st.markdown("### Key Requirements")
    for req in ats.get("key_requirements", []):
        st.markdown(f"- {req}")

    if st.button("Generate Tailoring Suggestions"):
        lines = st.session_state.resume_processor.get_all_lines()

        with st.spinner("Generating suggestions..."):
            suggestions = client.generate_suggestions(
                lines=lines,
                job_description=job_description,
                ats_analysis=ats,
            )
            st.session_state.suggestions = suggestions

        st.success("Suggestions generated.")

if st.session_state.suggestions:
    st.subheader("Choose Rewrites")

    for i, suggestion in enumerate(st.session_state.suggestions):
        st.markdown("---")
        st.write(f'**Original line [{suggestion["line_index"]}]**')
        st.code(suggestion["original"])

        st.write("Reason:")
        st.write(suggestion.get("reason", ""))

        selected = st.session_state.choices_made.get(i, None)

        for opt_idx, option in enumerate(suggestion["options"]):
            button_label = f"Use Option {opt_idx + 1} for line {suggestion['line_index']}"
            if st.button(button_label, key=f"choice_{i}_{opt_idx}"):
                st.session_state.choices_made[i] = option

        if selected:
            st.success("Selected rewrite:")
            st.code(selected)

    if st.button("Apply Selected Changes"):
        processor = st.session_state.resume_processor

        for i, suggestion in enumerate(st.session_state.suggestions):
            chosen_text = st.session_state.choices_made.get(i)
            if chosen_text:
                processor.replace_line(suggestion["line_index"], chosen_text)

        st.success("Selected changes applied to resume.")

    if st.button("Download Tailored Resume"):
        docx_bytes = st.session_state.resume_processor.export()
        st.download_button(
            label="Download .docx",
            data=docx_bytes,
            file_name="tailored_resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
