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
    page_title="Rizzume",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------
st.markdown("""
<style>
    :root {
        --bg: #071018;
        --bg-2: #0b1420;
        --panel: #101a28;
        --panel-2: #0f1724;
        --panel-3: #131f30;
        --stroke: rgba(255,255,255,0.08);
        --stroke-strong: rgba(255,255,255,0.12);
        --text: #f4f7fb;
        --muted: #b8c2cf;
        --soft: #8e9aab;
        --accent: #7aa2ff;
        --accent-2: #5b8cff;
        --success: #2ecc71;
        --warn: #f59e0b;
        --danger: #ff5d5d;
        --shadow: 0 18px 50px rgba(0,0,0,0.28);
        --shadow-soft: 0 10px 30px rgba(0,0,0,0.18);
        --radius-xl: 28px;
        --radius-lg: 22px;
        --radius-md: 16px;
        --radius-sm: 12px;
    }

    html, body, [class*="css"] {
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text);
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(90,140,255,0.09), transparent 28%),
            radial-gradient(circle at bottom right, rgba(75,117,209,0.08), transparent 24%),
            linear-gradient(180deg, #06101a 0%, #08121d 45%, #0b1420 100%);
    }

    .block-container {
        max-width: 1380px;
        padding-top: 1.1rem;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] {
        display: none;
    }

    /* Hide Streamlit default top spacing artifacts a bit */
    header[data-testid="stHeader"] {
        background: transparent;
    }

    /* ---------------- Top bar ---------------- */
    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1rem;
        padding: 0.15rem 0.1rem 0.4rem 0.1rem;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 0.85rem;
    }

    .brand-badge {
        width: 44px;
        height: 44px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(180deg, #18263a, #101a28);
        border: 1px solid var(--stroke-strong);
        color: #ffffff;
        font-size: 1rem;
        font-weight: 800;
        box-shadow: var(--shadow-soft);
    }

    .brand-title {
        font-size: 1.12rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: 0.01em;
        line-height: 1.1;
    }

    .brand-sub {
        font-size: 0.84rem;
        color: var(--soft);
        margin-top: 0.15rem;
    }

    .topbar-right {
        display: flex;
        gap: 0.55rem;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .status-pill {
        padding: 0.48rem 0.78rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.04);
        border: 1px solid var(--stroke);
        color: #d8e1ec;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* ---------------- Hero ---------------- */
    .hero-shell {
        position: relative;
        overflow: hidden;
        border-radius: 30px;
        padding: 2.2rem;
        border: 1px solid var(--stroke);
        background:
            linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02)),
            linear-gradient(180deg, #0b1524, #0a1320);
        box-shadow: var(--shadow);
        margin-bottom: 1.15rem;
    }

    .hero-grid {
        display: grid;
        grid-template-columns: 1.4fr 0.8fr;
        gap: 1.2rem;
        align-items: stretch;
    }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.42rem 0.75rem;
        border-radius: 999px;
        background: rgba(122,162,255,0.10);
        border: 1px solid rgba(122,162,255,0.18);
        color: #c9d9ff;
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .hero-title {
        font-size: clamp(2.4rem, 4vw, 4rem);
        line-height: 1.02;
        letter-spacing: -0.045em;
        margin: 0 0 0.75rem 0;
        font-weight: 900;
        color: #ffffff;
        max-width: 760px;
    }

    .brand-highlight {
        color: #dbe8ff;
    }

    .hero-sub {
        font-size: 1rem;
        line-height: 1.75;
        color: #c2ccd8;
        max-width: 760px;
        margin-bottom: 1rem;
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 0.3rem;
    }

    .pill {
        padding: 0.56rem 0.84rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.04);
        border: 1px solid var(--stroke);
        color: #e9eff8;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .hero-stat-panel {
        height: 100%;
        border-radius: 24px;
        padding: 1.2rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
        border: 1px solid var(--stroke);
        box-shadow: var(--shadow-soft);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .hero-stat-kicker {
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.11em;
        font-weight: 800;
        color: var(--soft);
        margin-bottom: 0.45rem;
    }

    .hero-stat-big {
        font-size: 2.4rem;
        font-weight: 900;
        letter-spacing: -0.04em;
        color: white;
        margin: 0 0 0.25rem 0;
    }

    .hero-stat-copy {
        font-size: 0.95rem;
        color: #c0cad6;
        line-height: 1.65;
    }

    .mini-metrics {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.7rem;
        margin-top: 1rem;
    }

    .mini-metric {
        border-radius: 16px;
        padding: 0.9rem;
        background: rgba(255,255,255,0.03);
        border: 1px solid var(--stroke);
    }

    .mini-metric-label {
        font-size: 0.72rem;
        color: var(--soft);
        text-transform: uppercase;
        font-weight: 800;
        letter-spacing: 0.08em;
        margin-bottom: 0.25rem;
    }

    .mini-metric-value {
        font-size: 1rem;
        color: white;
        font-weight: 800;
    }

    /* ---------------- Section cards ---------------- */
    .section-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.02));
        border: 1px solid var(--stroke);
        border-radius: var(--radius-xl);
        padding: 1.2rem 1.2rem 1rem 1.2rem;
        box-shadow: var(--shadow-soft);
        margin-bottom: 1rem;
    }

    .mini-step {
        display: inline-block;
        padding: 0.35rem 0.65rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 800;
        background: rgba(122,162,255,0.10);
        color: #d6e3ff;
        border: 1px solid rgba(122,162,255,0.18);
        margin-bottom: 0.65rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .section-title {
        font-size: 1.22rem;
        font-weight: 800;
        margin-bottom: 0.18rem;
        color: white;
        letter-spacing: -0.02em;
    }

    .section-sub {
        color: #b8c4d2;
        font-size: 0.95rem;
        margin-bottom: 0;
        line-height: 1.6;
    }

    /* ---------------- Labels ---------------- */
    .stFileUploader label,
    .stTextArea label,
    .stRadio label,
    label {
        color: #f2f6fb !important;
        font-weight: 700 !important;
    }

    /* ---------------- File uploader ---------------- */
    div[data-testid="stFileUploader"] {
        border: 1px dashed rgba(255,255,255,0.14);
        border-radius: 20px;
        padding: 0.6rem;
        background: rgba(255,255,255,0.03);
    }

    div[data-testid="stFileUploader"] section {
        background: transparent !important;
    }

    /* ---------------- Text area FIX ---------------- */
    div[data-testid="stTextArea"] textarea,
    .stTextArea textarea {
        border-radius: 18px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        background: #f5f7fb !important;
        color: #101828 !important;
        -webkit-text-fill-color: #101828 !important;
        padding: 1rem !important;
        min-height: 260px !important;
        box-shadow: none !important;
        font-weight: 500 !important;
        line-height: 1.6 !important;
        caret-color: #101828 !important;
    }

    div[data-testid="stTextArea"] textarea::placeholder,
    .stTextArea textarea::placeholder {
        color: #667085 !important;
        opacity: 1 !important;
    }

    div[data-testid="stTextArea"] textarea:focus,
    .stTextArea textarea:focus {
        border: 1px solid rgba(122,162,255,0.55) !important;
        box-shadow: 0 0 0 3px rgba(122,162,255,0.18) !important;
        outline: none !important;
    }

    /* ---------------- Buttons ---------------- */
    .stButton > button,
    .stDownloadButton > button {
        width: 100%;
        border-radius: 16px !important;
        min-height: 3rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em;
        border: 1px solid rgba(255,255,255,0.10) !important;
        background: linear-gradient(180deg, #1a2434, #141d2b) !important;
        color: white !important;
        box-shadow: 0 10px 24px rgba(0,0,0,0.18);
        transition: all 0.18s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        border-color: rgba(122,162,255,0.34) !important;
        background: linear-gradient(180deg, #223048, #182335) !important;
        transform: translateY(-1px);
    }

    /* ---------------- Progress ---------------- */
    div[data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #7aa2ff, #5b8cff) !important;
    }

    /* ---------------- Metrics ---------------- */
    .metric-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
        padding: 1rem;
        border-radius: 22px;
        border: 1px solid var(--stroke);
        box-shadow: var(--shadow-soft);
    }

    [data-testid="metric-container"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    [data-testid="metric-container"] label {
        color: #9fb0c4 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.72rem !important;
    }

    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 2rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.03em;
    }

    /* ---------------- Keyword boxes ---------------- */
    .keyword-box {
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
        border: 1px solid var(--stroke);
        border-radius: 22px;
        padding: 1rem;
        min-height: 220px;
        box-shadow: var(--shadow-soft);
    }

    .keyword-title {
        font-weight: 800;
        margin-bottom: 0.8rem;
        font-size: 1rem;
        color: white;
    }

    .chip-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .chip-good {
        background: rgba(46,204,113,0.12);
        color: #d1f7df;
        border: 1px solid rgba(46,204,113,0.24);
        padding: 0.4rem 0.7rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 700;
    }

    .chip-missing {
        background: rgba(245,158,11,0.12);
        color: #fde8bf;
        border: 1px solid rgba(245,158,11,0.22);
        padding: 0.4rem 0.7rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 700;
    }

    /* ---------------- Requirement items ---------------- */
    .req-item {
        padding: 0.85rem 1rem;
        border-radius: 16px;
        background: rgba(255,255,255,0.03);
        border: 1px solid var(--stroke);
        margin-bottom: 0.6rem;
        color: #d5deea;
        line-height: 1.6;
    }

    /* ---------------- Suggestion cards ---------------- */
    .suggestion-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
        border: 1px solid var(--stroke);
        border-radius: 24px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-soft);
    }

    .line-label {
        font-size: 0.78rem;
        color: #aeb9c7;
        font-weight: 800;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    }

    .reason-box {
        background: rgba(122,162,255,0.08);
        border: 1px solid rgba(122,162,255,0.16);
        padding: 0.9rem 1rem;
        border-radius: 14px;
        color: #d7e4ff;
        margin-top: 0.8rem;
        margin-bottom: 0.9rem;
        line-height: 1.6;
    }

    /* Code block readability */
    div[data-testid="stCodeBlock"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
    }

    div[data-testid="stCodeBlock"] pre,
    div[data-testid="stCodeBlock"] code {
        white-space: pre-wrap !important;
        word-break: break-word !important;
        overflow-wrap: anywhere !important;
    }

    details {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 0.35rem 0.7rem;
    }

    /* ---------------- RADIO FIX ---------------- */
    div[data-testid="stRadio"] > div {
        gap: 0.7rem;
    }

    div[data-testid="stRadio"] label {
        color: #eef4fb !important;
    }

    div[role="radiogroup"] {
        gap: 0.75rem !important;
    }

    div[role="radiogroup"] > label {
        background: #101a28 !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 18px !important;
        padding: 0.95rem 1rem !important;
        margin-bottom: 0.7rem !important;
        transition: all 0.2s ease;
        display: flex !important;
        align-items: center !important;
        min-height: 64px !important;
    }

    div[role="radiogroup"] > label:hover {
        border-color: rgba(122,162,255,0.32) !important;
        background: #142033 !important;
    }

    div[role="radiogroup"] > label p,
    div[role="radiogroup"] > label span,
    div[role="radiogroup"] > label div {
        color: #eef4fb !important;
        opacity: 1 !important;
        font-size: 1rem !important;
        line-height: 1.55 !important;
    }

    div[role="radiogroup"] > label[data-baseweb="radio"] {
        width: 100%;
    }

    /* More aggressive fix for dim text in options */
    div[data-testid="stMarkdownContainer"] p {
        color: inherit;
    }

    /* ---------------- Download ---------------- */
    .download-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
        color: white;
        border-radius: 24px;
        padding: 1.2rem;
        border: 1px solid var(--stroke);
        box-shadow: var(--shadow);
        margin-top: 1rem;
    }

    .download-title {
        font-size: 1.24rem;
        font-weight: 850;
        margin-bottom: 0.28rem;
        color: white;
    }

    .download-sub {
        color: #bcc8d6;
        margin-bottom: 1rem;
        line-height: 1.65;
    }

    .footer-note {
        text-align: center;
        color: #91a0b2;
        margin-top: 1rem;
        font-size: 0.9rem;
    }

    .success-banner {
        padding: 0.9rem 1rem;
        border-radius: 16px;
        background: rgba(46,204,113,0.10);
        border: 1px solid rgba(46,204,113,0.18);
        color: #d9fbe6;
        margin-bottom: 0.9rem;
    }

    /* Alerts improve contrast */
    div[data-baseweb="notification"] {
        border-radius: 16px !important;
    }

    /* ---------------- Responsive ---------------- */
    @media (max-width: 1050px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }

        .hero-title {
            font-size: 2.7rem;
        }

        .topbar {
            flex-direction: column;
            align-items: flex-start;
        }
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
# TOP BAR
# ---------------------------------------------------
st.markdown("""
<div class="topbar">
    <div class="brand">
        <div class="brand-badge">✦</div>
        <div>
            <div class="brand-title">Rizzume</div>
            <div class="brand-sub">Resume tailoring that looks clean and hits harder</div>
        </div>
    </div>
    <div class="topbar-right">
        <div class="status-pill">ATS Match</div>
        <div class="status-pill">Format Safe</div>
        <div class="status-pill">DOCX + PDF</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------
# HERO
# ---------------------------------------------------
st.markdown("""
<div class="hero-shell">
    <div class="hero-grid">
        <div>
            <div class="eyebrow">Smarter Resume Tailoring</div>
            <div class="hero-title">
                <span class="brand-highlight">Rizzume</span><br>
                Rizz up your recruiter
            </div>
            <div class="hero-sub">
                Upload your resume, paste the job description, and tailor each line without breaking the format.
                See keyword gaps, generate cleaner rewrites, and export a sharper final version.
            </div>
            <div class="pill-row">
                <div class="pill">ATS Analysis</div>
                <div class="pill">Keyword Match</div>
                <div class="pill">Line Rewrites</div>
                <div class="pill">Export Ready</div>
            </div>
        </div>
        <div class="hero-stat-panel">
            <div>
                <div class="hero-stat-kicker">What it does</div>
                <div class="hero-stat-big">Tailor faster</div>
                <div class="hero-stat-copy">
                    Compare your resume against the role, see what is missing, and update the lines that matter most without wrecking layout.
                </div>
            </div>
            <div class="mini-metrics">
                <div class="mini-metric">
                    <div class="mini-metric-label">Focus</div>
                    <div class="mini-metric-value">ATS + Clarity</div>
                </div>
                <div class="mini-metric">
                    <div class="mini-metric-label">Brand</div>
                    <div class="mini-metric-value">Rizzume ✦</div>
                </div>
            </div>
        </div>
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

st.progress(progress_steps / 4, text=f"Rizzume Workflow: {progress_steps}/4 complete")


# ---------------------------------------------------
# STEP 1 - INPUTS
# ---------------------------------------------------
st.markdown("""
<div class="section-card">
    <div class="mini-step">Step 01</div>
    <div class="section-title">Upload Resume and Job Description</div>
    <div class="section-sub">
        Start with your DOCX resume and the role you want to target.
    </div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 1.35], gap="large")

with left:
    uploaded_file = st.file_uploader("Upload your resume (.docx only)", type=["docx"])

with right:
    job_description = st.text_area(
        "Paste Job Description",
        height=260,
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
        st.markdown(
            '<div class="success-banner">Resume uploaded successfully. Ready to analyze and tailor.</div>',
            unsafe_allow_html=True
        )


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
    <div class="mini-step">Step 02</div>
    <div class="section-title">Analyze ATS Match</div>
    <div class="section-sub">
        See keyword coverage, missing terms, and key requirements before making edits.
    </div>
</div>
""", unsafe_allow_html=True)

analyze_col1, analyze_col2 = st.columns([1, 4], gap="large")

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
        present_html = "".join(
            [f'<span class="chip-good">{kw}</span>' for kw in present_keywords]
        ) if present_keywords else '<span style="color:#9fb0c4;">No keywords detected.</span>'

        st.markdown(f"""
        <div class="keyword-box">
            <div class="keyword-title">Present Keywords</div>
            <div class="chip-wrap">{present_html}</div>
        </div>
        """, unsafe_allow_html=True)

    with kw2:
        missing_keywords = ats.get("missing_keywords", [])
        missing_html = "".join(
            [f'<span class="chip-missing">{kw}</span>' for kw in missing_keywords]
        ) if missing_keywords else '<span style="color:#9fb0c4;">No missing keywords detected.</span>'

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

    gen_col1, gen_col2 = st.columns([1, 4], gap="large")
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
        <div class="mini-step">Step 03</div>
        <div class="section-title">Choose Better Rewrites</div>
        <div class="section-sub">
            Review suggestions line by line and keep only the changes you want.
        </div>
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
            st.markdown(
                f'<div class="reason-box"><strong>Why this was flagged:</strong> {reason}</div>',
                unsafe_allow_html=True
            )

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

    apply_col1, apply_col2 = st.columns([1, 4], gap="large")

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
    st.markdown('<div class="download-title">Download Your Final Resume</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="download-sub">Export your tailored DOCX, then generate a PDF once everything looks right.</div>',
        unsafe_allow_html=True
    )

    current_docx_bytes = (
        st.session_state.tailored_docx_bytes
        if st.session_state.tailored_docx_bytes is not None
        else st.session_state.resume_processor.export()
    )

    file_stem = get_file_stem(st.session_state.uploaded_filename or "resume.docx")

    d1, d2, d3 = st.columns([1, 1, 1.2], gap="large")

    with d1:
        st.download_button(
            label="Download DOCX",
            data=current_docx_bytes,
            file_name=f"{file_stem}_rizzume.docx",
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
                file_name=f"{file_stem}_rizzume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="footer-note">Rizzume — tailor faster, keep formatting, apply smarter.</div>',
    unsafe_allow_html=True
)
