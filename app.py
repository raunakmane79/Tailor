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
        --bg: #07111f;
        --bg2: #0b1527;
        --panel: rgba(255,255,255,0.06);
        --panel-strong: rgba(255,255,255,0.10);
        --stroke: rgba(255,255,255,0.10);
        --text: #f8fafc;
        --muted: rgba(248,250,252,0.72);
        --soft: rgba(248,250,252,0.52);
        --gold: #d4af37;
        --gold-soft: rgba(212,175,55,0.16);
        --silver: rgba(255,255,255,0.72);
        --green: #86efac;
        --orange: #fdba74;
        --danger: #fca5a5;
        --shadow: 0 24px 80px rgba(0,0,0,0.34);
        --shadow-soft: 0 16px 45px rgba(0,0,0,0.18);
        --radius-xl: 28px;
        --radius-lg: 22px;
        --radius-md: 16px;
    }

    html, body, [class*="css"] {
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text);
    }

    .stApp {
        background:
            radial-gradient(circle at 10% 10%, rgba(212,175,55,0.10), transparent 24%),
            radial-gradient(circle at 90% 0%, rgba(147,197,253,0.10), transparent 26%),
            radial-gradient(circle at 50% 100%, rgba(168,85,247,0.08), transparent 30%),
            linear-gradient(180deg, #020817 0%, #07111f 38%, #0b1527 100%);
    }

    .block-container {
        max-width: 1460px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] {
        display: none;
    }

    /* Top brand bar */
    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding: 0.8rem 0.2rem 0.4rem 0.2rem;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }

    .brand-badge {
        width: 46px;
        height: 46px;
        border-radius: 14px;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0.04)),
            linear-gradient(135deg, rgba(212,175,55,0.18), rgba(212,175,55,0.04));
        border: 1px solid rgba(255,255,255,0.12);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
        box-shadow: var(--shadow-soft);
        backdrop-filter: blur(16px);
    }

    .brand-title {
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: 0.02em;
        color: #ffffff;
    }

    .brand-sub {
        font-size: 0.84rem;
        color: var(--soft);
        margin-top: 0.1rem;
    }

    .topbar-right {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .status-pill {
        padding: 0.48rem 0.85rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        color: rgba(255,255,255,0.84);
        font-size: 0.82rem;
        font-weight: 600;
        backdrop-filter: blur(12px);
    }

    /* Hero */
    .hero-shell {
        position: relative;
        overflow: hidden;
        border-radius: 34px;
        padding: 2.6rem;
        border: 1px solid rgba(255,255,255,0.10);
        background:
            radial-gradient(circle at 0% 0%, rgba(212,175,55,0.12), transparent 26%),
            radial-gradient(circle at 100% 0%, rgba(96,165,250,0.12), transparent 22%),
            linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
        backdrop-filter: blur(18px);
        box-shadow: var(--shadow);
        margin-bottom: 1.35rem;
    }

    .hero-glow {
        position: absolute;
        inset: auto -80px -80px auto;
        width: 260px;
        height: 260px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(212,175,55,0.14), transparent 62%);
        pointer-events: none;
    }

    .hero-grid {
        display: grid;
        grid-template-columns: 1.35fr 0.85fr;
        gap: 1.4rem;
        align-items: stretch;
    }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.42rem 0.78rem;
        border-radius: 999px;
        background: rgba(212,175,55,0.10);
        border: 1px solid rgba(212,175,55,0.18);
        color: #f6deb0;
        font-size: 0.82rem;
        font-weight: 700;
        margin-bottom: 1rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .hero-title {
        font-size: clamp(2.5rem, 4vw, 4.3rem);
        line-height: 0.98;
        letter-spacing: -0.045em;
        margin: 0 0 0.85rem 0;
        font-weight: 900;
        color: #ffffff;
        max-width: 780px;
    }

    .gold {
        background: linear-gradient(135deg, #fff4cb 0%, #f2d789 35%, #d4af37 70%, #fff0ba 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .hero-sub {
        font-size: 1.04rem;
        line-height: 1.75;
        color: rgba(255,255,255,0.78);
        max-width: 760px;
        margin-bottom: 1.25rem;
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin-top: 0.3rem;
    }

    .pill {
        padding: 0.58rem 0.88rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.08);
        color: rgba(255,255,255,0.92);
        font-size: 0.88rem;
        font-weight: 600;
        backdrop-filter: blur(12px);
    }

    .hero-stat-panel {
        height: 100%;
        border-radius: 28px;
        padding: 1.25rem;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: var(--shadow-soft);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .hero-stat-kicker {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
        color: rgba(255,255,255,0.52);
    }

    .hero-stat-big {
        font-size: 2.8rem;
        font-weight: 900;
        letter-spacing: -0.04em;
        color: white;
        margin: 0.3rem 0 0.15rem 0;
    }

    .hero-stat-copy {
        font-size: 0.95rem;
        color: rgba(255,255,255,0.74);
        line-height: 1.65;
    }

    .mini-metrics {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.8rem;
        margin-top: 1.2rem;
    }

    .mini-metric {
        border-radius: 18px;
        padding: 0.95rem;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.07);
    }

    .mini-metric-label {
        font-size: 0.75rem;
        color: rgba(255,255,255,0.58);
        text-transform: uppercase;
        font-weight: 800;
        letter-spacing: 0.08em;
        margin-bottom: 0.28rem;
    }

    .mini-metric-value {
        font-size: 1.15rem;
        color: white;
        font-weight: 800;
    }

    /* Glass sections */
    .section-card {
        position: relative;
        background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: var(--radius-xl);
        padding: 1.35rem 1.35rem 1.1rem 1.35rem;
        box-shadow: var(--shadow-soft);
        backdrop-filter: blur(16px);
        margin-bottom: 1rem;
        overflow: hidden;
    }

    .section-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, rgba(212,175,55,0.07), transparent 24%, transparent 76%, rgba(255,255,255,0.03));
        pointer-events: none;
    }

    .mini-step {
        display: inline-block;
        padding: 0.38rem 0.68rem;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 800;
        background: rgba(212,175,55,0.14);
        color: #f5df9d;
        border: 1px solid rgba(212,175,55,0.18);
        margin-bottom: 0.7rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .section-title {
        font-size: 1.3rem;
        font-weight: 800;
        margin-bottom: 0.18rem;
        color: white;
        letter-spacing: -0.02em;
    }

    .section-sub {
        color: rgba(255,255,255,0.70);
        font-size: 0.95rem;
        margin-bottom: 0;
        line-height: 1.6;
    }

    /* Inputs */
    div[data-testid="stFileUploader"] {
        border: 1.5px dashed rgba(255,255,255,0.18);
        border-radius: 22px;
        padding: 0.6rem;
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(14px);
    }

    div[data-testid="stFileUploader"] section {
        background: transparent !important;
    }

    div[data-testid="stTextArea"] textarea {
        border-radius: 20px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        background: rgba(255,255,255,0.05) !important;
        color: white !important;
        padding: 1rem !important;
        min-height: 240px !important;
        box-shadow: none !important;
    }

    div[data-testid="stTextArea"] textarea::placeholder {
        color: rgba(255,255,255,0.42) !important;
    }

    label, .stFileUploader label, .stTextArea label {
        color: rgba(255,255,255,0.92) !important;
        font-weight: 700 !important;
    }

    /* Buttons */
    .stButton > button,
    .stDownloadButton > button {
        width: 100%;
        border-radius: 16px !important;
        height: 3rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em;
        border: 1px solid rgba(255,255,255,0.10) !important;
        background:
            linear-gradient(135deg, rgba(212,175,55,0.18), rgba(255,255,255,0.08)) !important;
        color: white !important;
        box-shadow: 0 14px 32px rgba(0,0,0,0.18);
        transition: all 0.2s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        border-color: rgba(212,175,55,0.34) !important;
        box-shadow: 0 18px 34px rgba(0,0,0,0.22);
    }

    /* Progress */
    div[data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #d4af37, #f4df9b) !important;
    }

    /* Metrics */
    .metric-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
        padding: 1rem;
        border-radius: 22px;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: var(--shadow-soft);
        backdrop-filter: blur(12px);
    }

    [data-testid="metric-container"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    [data-testid="metric-container"] label {
        color: rgba(255,255,255,0.66) !important;
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

    /* Keyword boxes */
    .keyword-box {
        background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 24px;
        padding: 1.1rem;
        min-height: 240px;
        box-shadow: var(--shadow-soft);
        backdrop-filter: blur(14px);
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
        gap: 0.55rem;
    }

    .chip-good {
        background: rgba(134,239,172,0.12);
        color: #c8f7d6;
        border: 1px solid rgba(134,239,172,0.22);
        padding: 0.45rem 0.72rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 700;
    }

    .chip-missing {
        background: rgba(251,191,36,0.12);
        color: #fde7b0;
        border: 1px solid rgba(251,191,36,0.22);
        padding: 0.45rem 0.72rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 700;
    }

    /* Req items */
    .req-item {
        padding: 0.9rem 1rem;
        border-radius: 18px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 0.65rem;
        color: rgba(255,255,255,0.84);
        line-height: 1.6;
    }

    /* Suggestion cards */
    .suggestion-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.05));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 26px;
        padding: 1.1rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-soft);
        backdrop-filter: blur(14px);
    }

    .line-label {
        font-size: 0.76rem;
        color: rgba(255,255,255,0.52);
        font-weight: 800;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .reason-box {
        background: rgba(212,175,55,0.10);
        border: 1px solid rgba(212,175,55,0.18);
        padding: 0.95rem 1rem;
        border-radius: 16px;
        color: rgba(255,255,255,0.86);
        margin-top: 0.8rem;
        margin-bottom: 0.95rem;
        line-height: 1.6;
    }

    /* Code / expander */
    div[data-testid="stCodeBlock"] {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
    }

    details {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 0.35rem 0.7rem;
    }

    /* Download */
    .download-card {
        background:
            radial-gradient(circle at 0% 0%, rgba(212,175,55,0.10), transparent 20%),
            linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
        color: white;
        border-radius: 28px;
        padding: 1.3rem;
        border: 1px solid rgba(255,255,255,0.10);
        box-shadow: var(--shadow);
        backdrop-filter: blur(16px);
        margin-top: 1rem;
    }

    .download-title {
        font-size: 1.28rem;
        font-weight: 850;
        margin-bottom: 0.3rem;
        color: white;
    }

    .download-sub {
        color: rgba(255,255,255,0.76);
        margin-bottom: 1rem;
        line-height: 1.65;
    }

    .footer-note {
        text-align: center;
        color: rgba(255,255,255,0.52);
        margin-top: 1.15rem;
        font-size: 0.9rem;
    }

    .success-banner {
        padding: 0.92rem 1rem;
        border-radius: 18px;
        background: rgba(134,239,172,0.10);
        border: 1px solid rgba(134,239,172,0.18);
        color: #d9fbe4;
        margin-bottom: 0.95rem;
    }

    /* Radio styling help */
    div[role="radiogroup"] > label {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 15px;
        padding: 0.72rem 0.82rem;
        margin-bottom: 0.55rem;
        transition: all 0.2s ease;
    }

    div[role="radiogroup"] > label:hover {
        border-color: rgba(212,175,55,0.22);
        background: rgba(255,255,255,0.07);
    }

    /* Responsive */
    @media (max-width: 1050px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }

        .hero-title {
            font-size: 2.6rem;
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
            <div class="brand-sub">Luxury AI resume tailoring for serious applicants</div>
        </div>
    </div>
    <div class="topbar-right">
        <div class="status-pill">ATS Precision</div>
        <div class="status-pill">Format Protected</div>
        <div class="status-pill">DOCX + PDF Ready</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------
# HERO
# ---------------------------------------------------
st.markdown("""
<div class="hero-shell">
    <div class="hero-glow"></div>
    <div class="hero-grid">
        <div>
            <div class="eyebrow">Elite Resume Tailoring</div>
            <div class="hero-title">
                Meet <span class="gold">Rizzume</span><br>
                Your Resume, But Hotter.
            </div>
            <div class="hero-sub">
                Turn a generic resume into a role-specific, ATS-smart, premium application asset.
                Upload your DOCX, paste the job description, compare keyword gaps, choose rewrites
                line by line, and export a polished final version without wrecking formatting.
            </div>
            <div class="pill-row">
                <div class="pill">Line-by-Line Rewrite Control</div>
                <div class="pill">Missing Keyword Detection</div>
                <div class="pill">Premium UX</div>
                <div class="pill">PDF Export</div>
            </div>
        </div>
        <div class="hero-stat-panel">
            <div>
                <div class="hero-stat-kicker">Product Promise</div>
                <div class="hero-stat-big">Luxury UI</div>
                <div class="hero-stat-copy">
                    Built to feel like a high-end career product, not a rough internal tool.
                    Clean glassmorphism, premium contrast, stronger hierarchy, and a sharper
                    candidate workflow from upload to download.
                </div>
            </div>
            <div class="mini-metrics">
                <div class="mini-metric">
                    <div class="mini-metric-label">Mode</div>
                    <div class="mini-metric-value">Professional</div>
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
    <div class="section-title">Upload Resume + Paste Job Description</div>
    <div class="section-sub">
        Start with your DOCX resume and the full target job description.
        Rizzume keeps the structure intact while optimizing content.
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
            '<div class="success-banner">Resume uploaded successfully. Rizzume is ready to analyze and tailor.</div>',
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
    <div class="section-title">Run ATS Analysis</div>
    <div class="section-sub">
        Get a clean breakdown of score, keyword coverage, and the strongest requirements before editing anything.
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
        present_html = "".join([f'<span class="chip-good">{kw}</span>' for kw in present_keywords]) \
            if present_keywords else '<span style="color:rgba(255,255,255,0.52);">No keywords detected.</span>'
        st.markdown(f"""
        <div class="keyword-box">
            <div class="keyword-title">Present Keywords</div>
            <div class="chip-wrap">{present_html}</div>
        </div>
        """, unsafe_allow_html=True)

    with kw2:
        missing_keywords = ats.get("missing_keywords", [])
        missing_html = "".join([f'<span class="chip-missing">{kw}</span>' for kw in missing_keywords]) \
            if missing_keywords else '<span style="color:rgba(255,255,255,0.52);">No missing keywords detected.</span>'
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
        <div class="section-title">Choose Your Rewrites</div>
        <div class="section-sub">
            Review each recommendation and pick the best option. Only your selected changes will be applied.
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
                f'<div class="reason-box"><strong>Why Rizzume flagged this:</strong> {reason}</div>',
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
    st.markdown('<div class="download-title">Export Your Final Rizzume</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="download-sub">Download the tailored DOCX instantly, then generate a PDF once everything looks perfect.</div>',
        unsafe_allow_html=True
    )

    current_docx_bytes = (
        st.session_state.tailored_docx_bytes
        if st.session_state.tailored_docx_bytes is not None
        else st.session_state.resume_processor.export()
    )

    file_stem = get_file_stem(st.session_state.uploaded_filename or "resume.docx")

    d1, d2, d3 = st.columns([1, 1, 1.3], gap="large")

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
    '<div class="footer-note">Rizzume — premium resume tailoring with formatting protection.</div>',
    unsafe_allow_html=True
)
