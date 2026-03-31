import os
import tempfile
import subprocess
import shutil
from pathlib import Path

import streamlit as st

from resume_processor import ResumeProcessor
from gemini_client import GeminiClient


# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="Resume Tailor AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    html, body, [class*="css"] {
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .hero {
        padding: 2rem 2rem 1.2rem 2rem;
        border-radius: 24px;
        background:
            radial-gradient(circle at top left, rgba(120,119,198,0.35), transparent 28%),
            radial-gradient(circle at top right, rgba(0,212,255,0.20), transparent 30%),
            linear-gradient(135deg, #111827 0%, #0f172a 45%, #111827 100%);
        color: white;
        box-shadow: 0 20px 50px rgba(0,0,0,0.25);
        margin-bottom: 1.2rem;
        border: 1px solid rgba(255,255,255,0.08);
    }

    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 0.4rem;
        letter-spacing: -0.02em;
    }

    .hero-sub {
        font-size: 1rem;
        color: rgba(255,255,255,0.82);
        margin-bottom: 1rem;
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 0.7rem;
    }

    .pill {
        padding: 0.45rem 0.8rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.12);
        font-size: 0.9rem;
        color: rgba(255,255,255,0.95);
    }

    .section-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(248,250,252,0.95));
        border: 1px solid rgba(15,23,42,0.08);
        border-radius: 22px;
        padding: 1.2rem 1.2rem 1rem 1.2rem;
        box-shadow: 0 12px 30px rgba(15,23,42,0.06);
        margin-bottom: 1rem;
    }

    .section-title {
        font-size: 1.2rem;
        font-weight: 750;
        margin-bottom: 0.2rem;
        color: #0f172a;
    }

    .section-sub {
        color: #475569;
        font-size: 0.96rem;
        margin-bottom: 1rem;
    }

    .mini-step {
        display: inline-block;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        background: #e2e8f0;
        color: #0f172a;
        margin-bottom: 0.55rem;
    }

    .metric-card {
        background: linear-gradient(180deg, #ffffff, #f8fafc);
        padding: 1rem;
        border-radius: 18px;
        border: 1px solid rgba(15,23,42,0.08);
        box-shadow: 0 6px 20px rgba(15,23,42,0.04);
    }

    .keyword-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 1rem;
        min-height: 220px;
    }

    .keyword-title {
        font-weight: 750;
        margin-bottom: 0.7rem;
        font-size: 1rem;
        color: #0f172a;
    }

    .chip-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .chip-good {
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
        padding: 0.38rem 0.7rem;
        border-radius: 999px;
        font-size: 0.86rem;
        font-weight: 600;
    }

    .chip-missing {
        background: #fff7ed;
        color: #9a3412;
        border: 1px solid #fdba74;
        padding: 0.38rem 0.7rem;
        border-radius: 999px;
        font-size: 0.86rem;
        font-weight: 600;
    }

    .req-item {
        padding: 0.65rem 0.8rem;
        border-radius: 14px;
        background: white;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.55rem;
        color: #334155;
    }

    .suggestion-card {
        background: linear-gradient(180deg, #ffffff, #f8fafc);
        border: 1px solid #e2e8f0;
        border-radius: 22px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 10px 22px rgba(15,23,42,0.05);
    }

    .line-label {
        font-size: 0.82rem;
        color: #64748b;
        font-weight: 700;
        margin-bottom: 0.3rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .reason-box {
        background: #f8fafc;
        border-left: 4px solid #6366f1;
        padding: 0.85rem 1rem;
        border-radius: 12px;
        color: #334155;
        margin-top: 0.6rem;
        margin-bottom: 0.8rem;
    }

    .download-card {
        background: linear-gradient(135deg, #0f172a 0%, #111827 100%);
        color: white;
        border-radius: 22px;
        padding: 1.2rem;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 18px 40px rgba(0,0,0,0.18);
    }

    .download-title {
        font-size: 1.2rem;
        font-weight: 800;
        margin-bottom: 0.3rem;
    }

    .download-sub {
        color: rgba(255,255,255,0.8);
        margin-bottom: 1rem;
    }

    div[data-testid="stFileUploader"] {
        border: 2px dashed #cbd5e1;
        border-radius: 18px;
        padding: 0.4rem;
        background: #f8fafc;
    }

    div[data-testid="stTextArea"] textarea {
        border-radius: 16px !important;
    }

    div[data-testid="stCodeBlock"] {
        border-radius: 16px;
    }

    .footer-note {
        text-align: center;
        color: #64748b;
        margin-top: 1rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------
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


# ---------------------------------------------------
# GEMINI / SECRETS
# ---------------------------------------------------
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("GEMINI_API_KEY not found in Streamlit secrets.")
    st.stop()

client = GeminiClient(GEMINI_API_KEY)


# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------
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


# ---------------------------------------------------
# HERO
# ---------------------------------------------------
st.markdown("""
<div class="hero">
    <div class="hero-title">Resume Tailor AI ✦</div>
    <div class="hero-sub">
        Transform your resume for each job description without breaking formatting.
        Clean ATS analysis, line-by-line rewrites, and export-ready output.
    </div>
    <div class="pill-row">
        <div class="pill">ATS Match Analysis</div>
        <div class="pill">Format-Safe Rewrites</div>
        <div class="pill">Multiple Rewrite Options</div>
        <div class="pill">DOCX + PDF Export</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------
# PROGRESS OVERVIEW
# ---------------------------------------------------
progress_steps = 0
if st.session_state.resume_processor is not None:
    progress_steps = 1
if st.session_state.ats_analysis:
    progress_steps = 2
if st.session_state.suggestions:
    progress_steps = 3
if st.session_state.tailored_docx_bytes is not None:
    progress_steps = 4

st.progress(progress_steps / 4, text=f"Workflow Progress: {progress_steps}/4 complete")


# ---------------------------------------------------
# STEP 1 - INPUTS
# ---------------------------------------------------
st.markdown("""
<div class="section-card">
    <div class="mini-step">STEP 1</div>
    <div class="section-title">Upload Resume + Paste Job Description</div>
    <div class="section-sub">Start with your DOCX resume and the target job description.</div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 1.4], gap="large")

with left:
    uploaded_file = st.file_uploader("Upload your resume (.docx only)", type=["docx"])

with right:
    job_description = st.text_area(
        "Paste Job Description",
        height=240,
        placeholder="Paste the full job description here..."
    )

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    current_signature = (uploaded_file.name, len(file_bytes))

    if st.session_state.uploaded_file_signature != current_signature:
        st.session_state.resume_processor = ResumeProcessor(file_bytes)
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.uploaded_file_signature = current_signature
        reset_state_for_new_file()
        st.success("Resume uploaded successfully.")


# ---------------------------------------------------
# OPTIONAL PREVIEW
# ---------------------------------------------------
if st.session_state.resume_processor is not None:
    with st.expander("Preview extracted resume lines"):
        lines = st.session_state.resume_processor.get_all_lines()
        for line in lines:
            if line["text"].strip():
                st.write(f'**[{line["index"]}]** · {line["char_count"]} chars')
                st.code(line["text"])


# ---------------------------------------------------
# STEP 2 - ATS ANALYSIS
# ---------------------------------------------------
st.markdown("""
<div class="section-card">
    <div class="mini-step">STEP 2</div>
    <div class="section-title">Run ATS Analysis</div>
    <div class="section-sub">See how well your resume matches the job description before rewriting anything.</div>
</div>
""", unsafe_allow_html=True)

analyze_col1, analyze_col2, analyze_col3 = st.columns([1, 1, 4])

with analyze_col1:
    analyze_clicked = st.button("Analyze ATS Match", use_container_width=True)

if analyze_clicked:
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


# ---------------------------------------------------
# ATS RESULTS
# ---------------------------------------------------
if st.session_state.ats_analysis:
    ats = st.session_state.ats_analysis
    ats_score = int(ats.get("ats_score", 0))

    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("ATS Score", f"{ats_score}%")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Present Keywords", len(ats.get("present_keywords", [])))
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Missing Keywords", len(ats.get("missing_keywords", [])))
        st.markdown('</div>', unsafe_allow_html=True)

    if ats.get("score_note"):
        st.info(ats.get("score_note"))

    kw1, kw2 = st.columns(2, gap="large")

    with kw1:
        present_keywords = ats.get("present_keywords", [])
        present_html = "".join([f'<span class="chip-good">{kw}</span>' for kw in present_keywords]) \
            if present_keywords else '<span style="color:#64748b;">No keywords detected.</span>'
        st.markdown(f"""
        <div class="keyword-box">
            <div class="keyword-title">Present Keywords</div>
            <div class="chip-wrap">{present_html}</div>
        </div>
        """, unsafe_allow_html=True)

    with kw2:
        missing_keywords = ats.get("missing_keywords", [])
        missing_html = "".join([f'<span class="chip-missing">{kw}</span>' for kw in missing_keywords]) \
            if missing_keywords else '<span style="color:#64748b;">No missing keywords detected.</span>'
        st.markdown(f"""
        <div class="keyword-box">
            <div class="keyword-title">Missing Keywords</div>
            <div class="chip-wrap">{missing_html}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Key Requirements")
    key_requirements = ats.get("key_requirements", [])
    if key_requirements:
        for req in key_requirements:
            st.markdown(f'<div class="req-item">{req}</div>', unsafe_allow_html=True)
    else:
        st.caption("No key requirements returned.")

    gen_col1, gen_col2 = st.columns([1, 4])
    with gen_col1:
        generate_clicked = st.button("Generate Suggestions", use_container_width=True)

    if generate_clicked:
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


# ---------------------------------------------------
# STEP 3 - SUGGESTION CHOICES
# ---------------------------------------------------
if st.session_state.suggestions:
    st.markdown("""
    <div class="section-card">
        <div class="mini-step">STEP 3</div>
        <div class="section-title">Choose Your Rewrites</div>
        <div class="section-sub">Pick the best rewrite for each line. Only selected changes will be applied.</div>
    </div>
    """, unsafe_allow_html=True)

    total_suggestions = len(st.session_state.suggestions)
    selected_count = len(st.session_state.choices_made)
    st.progress(
        selected_count / total_suggestions if total_suggestions else 0,
        text=f"Selections made: {selected_count}/{total_suggestions}"
    )

    for i, suggestion in enumerate(st.session_state.suggestions):
        line_index = suggestion.get("line_index", "Unknown")
        original = suggestion.get("original", "")
        options = suggestion.get("options", [])
        reason = suggestion.get("reason", "")

        st.markdown('<div class="suggestion-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="line-label">Resume Line {line_index}</div>', unsafe_allow_html=True)
        st.code(original, language=None)

        if reason:
            st.markdown(f'<div class="reason-box"><strong>Why change it:</strong> {reason}</div>', unsafe_allow_html=True)

        radio_options = ["Keep original"] + options
        current_value = st.session_state.choices_made.get(i, "Keep original")

        selected = st.radio(
            f"Choose best option for line {line_index}",
            radio_options,
            index=radio_options.index(current_value) if current_value in radio_options else 0,
            key=f"radio_{i}",
            label_visibility="collapsed"
        )

        if selected == "Keep original":
            st.session_state.choices_made.pop(i, None)
        else:
            st.session_state.choices_made[i] = selected

        st.markdown('</div>', unsafe_allow_html=True)

    apply_col1, apply_col2 = st.columns([1, 4])

    with apply_col1:
        apply_clicked = st.button("Apply Selected Changes", use_container_width=True)

    if apply_clicked:
        processor = st.session_state.resume_processor

        if processor is None:
            st.error("Resume processor not found. Please re-upload your resume.")
        else:
            try:
                processor = ResumeProcessor(uploaded_file.getvalue()) if uploaded_file else processor

                for i, suggestion in enumerate(st.session_state.suggestions):
                    chosen_text = st.session_state.choices_made.get(i)
                    if chosen_text:
                        processor.replace_line(suggestion["line_index"], chosen_text)

                st.session_state.resume_processor = processor
                st.session_state.tailored_docx_bytes = processor.export()
                st.session_state.pdf_bytes = None
                st.success("Selected changes applied to resume.")
            except Exception as e:
                st.error(f"Applying changes failed: {e}")


# ---------------------------------------------------
# STEP 4 - DOWNLOAD
# ---------------------------------------------------
if st.session_state.resume_processor is not None:
    st.markdown('<div class="download-card">', unsafe_allow_html=True)
    st.markdown('<div class="download-title">Download Your Tailored Resume</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="download-sub">Export the final version in DOCX, and optionally generate a PDF.</div>',
        unsafe_allow_html=True
    )

    current_docx_bytes = (
        st.session_state.tailored_docx_bytes
        if st.session_state.tailored_docx_bytes is not None
        else st.session_state.resume_processor.export()
    )

    file_stem = get_file_stem(st.session_state.uploaded_filename or "resume.docx")

    d1, d2, d3 = st.columns([1, 1, 2], gap="large")

    with d1:
        st.download_button(
            label="Download DOCX",
            data=current_docx_bytes,
            file_name=f"{file_stem}_tailored.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    with d2:
        if SOFFICE_AVAILABLE:
            if st.button("Generate PDF", use_container_width=True):
                with st.spinner("Converting to PDF..."):
                    try:
                        st.session_state.pdf_bytes = convert_docx_to_pdf_bytes(current_docx_bytes)
                        st.success("PDF ready.")
                    except Exception as e:
                        st.error(f"PDF conversion failed: {e}")
        else:
            st.caption("PDF export unavailable on this deployment.")

    with d3:
        if st.session_state.pdf_bytes is not None:
            st.download_button(
                label="Download PDF",
                data=st.session_state.pdf_bytes,
                file_name=f"{file_stem}_tailored.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="footer-note">For best formatting, upload DOCX and export to PDF only after finalizing all edits.</div>',
    unsafe_allow_html=True
)
