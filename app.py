import os
import tempfile
import subprocess
import shutil
from pathlib import Path

import streamlit as st

from resume_processor import ResumeProcessor
from gemini_client import GeminiClient


st.set_page_config(
    page_title="Resume Tailor AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("Resume Tailor AI")
st.caption("ATS-Optimized · Format-Safe · Gemini-Powered · PDF Export")


def get_file_stem(filename: str) -> str:
    return Path(filename).stem if filename else "tailored_resume"


def reset_state_for_new_file() -> None:
    st.session_state.ats_analysis = None
    st.session_state.suggestions = []
    st.session_state.choices_made = {}
    st.session_state.pdf_bytes = None
    st.session_state.tailored_docx_bytes = None


def convert_docx_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_docx = os.path.join(tmpdir, "resume.docx")
        output_pdf = os.path.join(tmpdir, "resume.pdf")

        with open(input_docx, "wb") as f:
            f.write(docx_bytes)

        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                input_docx,
                "--outdir",
                tmpdir,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice conversion failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )

        if not os.path.exists(output_pdf):
            raise RuntimeError("PDF file was not created.")

        with open(output_pdf, "rb") as f:
            return f.read()


SOFFICE_AVAILABLE = shutil.which("soffice") is not None


# -----------------------------
# Secrets / Gemini setup
# -----------------------------
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("GEMINI_API_KEY not found in Streamlit secrets.")
    st.stop()

client = GeminiClient(GEMINI_API_KEY)


# -----------------------------
# Session state
# -----------------------------
defaults = {
    "resume_processor": None,
    "ats_analysis": None,
    "suggestions": [],
    "choices_made": {},
    "pdf_bytes": None,
    "tailored_docx_bytes": None,
    "uploaded_filename": None,
    "uploaded_file_signature": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -----------------------------
# Upload section
# -----------------------------
uploaded_file = st.file_uploader("Upload your resume (.docx only)", type=["docx"])
job_description = st.text_area("Paste Job Description", height=250)

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    current_signature = (uploaded_file.name, len(file_bytes))

    if st.session_state.uploaded_file_signature != current_signature:
        st.session_state.resume_processor = ResumeProcessor(file_bytes)
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.uploaded_file_signature = current_signature
        reset_state_for_new_file()
        st.success("Resume uploaded successfully.")


# -----------------------------
# Preview extracted lines
# -----------------------------
if st.session_state.resume_processor is not None:
    with st.expander("Preview extracted resume lines"):
        lines = st.session_state.resume_processor.get_all_lines()
        for line in lines:
            if line["text"].strip():
                st.write(f'[{line["index"]}] ({line["char_count"]} chars) {line["text"]}')


# -----------------------------
# ATS analysis
# -----------------------------
if st.button("Analyze ATS Match"):
    if st.session_state.resume_processor is None:
        st.warning("Please upload a resume first.")
    elif not job_description.strip():
        st.warning("Please paste the job description.")
    else:
        resume_text = "\n".join(
            line["text"]
            for line in st.session_state.resume_processor.get_all_lines()
            if line["text"].strip()
        )

        with st.spinner("Analyzing ATS match..."):
            try:
                ats_analysis = client.analyze_ats(resume_text, job_description)
                st.session_state.ats_analysis = ats_analysis
                st.session_state.suggestions = []
                st.session_state.choices_made = {}
                st.session_state.tailored_docx_bytes = None
                st.session_state.pdf_bytes = None
                st.success("ATS analysis complete.")
            except Exception as e:
                st.error(f"ATS analysis failed: {e}")


# -----------------------------
# ATS results
# -----------------------------
if st.session_state.ats_analysis:
    ats = st.session_state.ats_analysis

    st.subheader("ATS Analysis")
    st.metric("ATS Score", f'{ats.get("ats_score", 0)}%')
    st.write(ats.get("score_note", ""))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Present Keywords")
        present_keywords = ats.get("present_keywords", [])
        if present_keywords:
            for kw in present_keywords:
                st.markdown(f"- {kw}")
        else:
            st.caption("No keywords detected.")

    with col2:
        st.markdown("### Missing Keywords")
        missing_keywords = ats.get("missing_keywords", [])
        if missing_keywords:
            for kw in missing_keywords:
                st.markdown(f"- {kw}")
        else:
            st.caption("No missing keywords detected.")

    st.markdown("### Key Requirements")
    key_requirements = ats.get("key_requirements", [])
    if key_requirements:
        for req in key_requirements:
            st.markdown(f"- {req}")
    else:
        st.caption("No key requirements returned.")

    if st.button("Generate Tailoring Suggestions"):
        lines = st.session_state.resume_processor.get_all_lines()

        with st.spinner("Generating suggestions..."):
            try:
                suggestions = client.generate_suggestions(
                    lines=lines,
                    job_description=job_description,
                    ats_analysis=ats,
                )
                st.session_state.suggestions = suggestions
                st.session_state.choices_made = {}
                st.session_state.tailored_docx_bytes = None
                st.session_state.pdf_bytes = None

                if suggestions:
                    st.success("Suggestions generated.")
                else:
                    st.warning("No suggestions were returned. Try a different job description or resume.")
            except Exception as e:
                st.error(f"Suggestion generation failed: {e}")


# -----------------------------
# Suggestion selection UI
# -----------------------------
if st.session_state.suggestions:
    st.subheader("Choose Rewrites")

    for i, suggestion in enumerate(st.session_state.suggestions):
        st.markdown("---")
        line_index = suggestion.get("line_index", "Unknown")
        original = suggestion.get("original", "")
        options = suggestion.get("options", [])
        reason = suggestion.get("reason", "")

        st.write(f"**Original line [{line_index}]**")
        st.code(original)
        st.write("Reason:")
        st.write(reason)

        selected = st.session_state.choices_made.get(i)

        for opt_idx, option in enumerate(options):
            st.code(option)
            button_text = f"Use Option {opt_idx + 1} for line {line_index}"
            if st.button(button_text, key=f"choice_{i}_{opt_idx}"):
                st.session_state.choices_made[i] = option
                st.rerun()

        if selected:
            st.success("Selected rewrite:")
            st.code(selected)

    if st.button("Apply Selected Changes"):
        processor = st.session_state.resume_processor

        if processor is None:
            st.error("Resume processor not found. Please re-upload your resume.")
        else:
            try:
                for i, suggestion in enumerate(st.session_state.suggestions):
                    chosen_text = st.session_state.choices_made.get(i)
                    if chosen_text:
                        processor.replace_line(suggestion["line_index"], chosen_text)

                st.session_state.tailored_docx_bytes = processor.export()
                st.session_state.pdf_bytes = None
                st.success("Selected changes applied to resume.")
            except Exception as e:
                st.error(f"Applying changes failed: {e}")


# -----------------------------
# Download section
# -----------------------------
if st.session_state.resume_processor is not None:
    st.markdown("---")
    st.subheader("Download Your Tailored Resume")

    current_docx_bytes = (
        st.session_state.tailored_docx_bytes
        if st.session_state.tailored_docx_bytes is not None
        else st.session_state.resume_processor.export()
    )

    file_stem = get_file_stem(st.session_state.uploaded_filename or "resume.docx")

    col_docx, col_pdf = st.columns(2)

    with col_docx:
        st.download_button(
            label="Download DOCX",
            data=current_docx_bytes,
            file_name=f"{file_stem}_tailored.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    with col_pdf:
        if SOFFICE_AVAILABLE:
            if st.button("Generate PDF"):
                with st.spinner("Converting to PDF..."):
                    try:
                        st.session_state.pdf_bytes = convert_docx_to_pdf_bytes(current_docx_bytes)
                        st.success("PDF ready.")
                    except Exception as e:
                        st.error(f"PDF conversion failed: {e}")

            if st.session_state.pdf_bytes is not None:
                st.download_button(
                    label="Download PDF",
                    data=st.session_state.pdf_bytes,
                    file_name=f"{file_stem}_tailored.pdf",
                    mime="application/pdf",
                )
        else:
            st.caption("PDF export is unavailable on this deployment. Download DOCX instead.")

st.info("For best formatting, keep uploads in DOCX format and export to PDF only at the end.")
)
