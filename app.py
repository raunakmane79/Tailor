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
# CUSTOM CSS — PREMIUM UI
# ---------------------------------------------------
st.markdown(
    """
<style>
    :root {
        --bg: #061019;
        --bg-2: #091321;
        --panel: rgba(13, 22, 35, 0.70);
        --panel-2: rgba(15, 24, 38, 0.78);
        --panel-3: rgba(18, 30, 46, 0.82);
        --stroke: rgba(255,255,255,0.08);
        --stroke-strong: rgba(255,255,255,0.14);
        --text: #f5f8fc;
        --muted: #b6c1cf;
        --soft: #8b98aa;
        --accent: #7aa2ff;
        --accent-2: #5d8dff;
        --accent-3: #a7c2ff;
        --success: #2ecc71;
        --warn: #f59e0b;
        --danger: #ff6464;
        --shadow: 0 24px 70px rgba(0,0,0,0.34);
        --shadow-soft: 0 16px 40px rgba(0,0,0,0.22);
        --radius-2xl: 32px;
        --radius-xl: 28px;
        --radius-lg: 22px;
        --radius-md: 18px;
        --radius-sm: 14px;
    }

    html, body, [class*="css"] {
        font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--text);
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 10%, rgba(122,162,255,0.18), transparent 28%),
            radial-gradient(circle at 88% 18%, rgba(93,141,255,0.12), transparent 22%),
            radial-gradient(circle at 80% 88%, rgba(122,162,255,0.10), transparent 24%),
            linear-gradient(180deg, #050c14 0%, #08111c 38%, #0a1320 100%);
    }

    .block-container {
        max-width: 1380px;
        padding-top: 1.35rem;
        padding-bottom: 3rem;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    section[data-testid="stSidebar"] {
        display: none;
    }

    div[data-testid="stToolbar"] {
        right: 1rem;
    }

    /* Hide Streamlit menu decoration spacing a bit */
    [data-testid="collapsedControl"] {
        display: none;
    }

    /* Global cards */
    .glass {
        position: relative;
        overflow: hidden;
        background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.025));
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border: 1px solid var(--stroke);
        box-shadow: var(--shadow-soft);
    }

    .glass::before {
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at top left, rgba(122,162,255,0.10), transparent 30%);
        pointer-events: none;
    }

    /* ---------------- Top bar ---------------- */
    .topbar {
        position: sticky;
        top: 0.6rem;
        z-index: 100;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1rem;
        padding: 0.9rem 1rem;
        border-radius: 22px;
        background: rgba(8, 14, 24, 0.72);
        border: 1px solid rgba(255,255,255,0.08);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 12px 30px rgba(0,0,0,0.18);
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }

    .brand-badge {
        width: 48px;
        height: 48px;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, rgba(122,162,255,0.18), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.12);
        color: #fff;
        font-size: 1.05rem;
        font-weight: 900;
        box-shadow: 0 12px 24px rgba(91,140,255,0.14);
    }

    .brand-title {
        font-size: 1.12rem;
        font-weight: 900;
        color: #ffffff;
        letter-spacing: -0.03em;
        line-height: 1.05;
    }

    .brand-sub {
        font-size: 0.84rem;
        color: var(--soft);
        margin-top: 0.12rem;
    }

    .topbar-right {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .status-pill {
        padding: 0.52rem 0.82rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        color: #dbe6f3;
        font-size: 0.79rem;
        font-weight: 700;
        letter-spacing: 0.01em;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }

    /* ---------------- Hero ---------------- */
    .hero-shell {
        position: relative;
        overflow: hidden;
        border-radius: var(--radius-2xl);
        padding: 2.35rem;
        border: 1px solid var(--stroke);
        background:
            linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)),
            linear-gradient(180deg, rgba(10,18,31,0.92), rgba(9,17,28,0.90));
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        box-shadow: var(--shadow);
        margin-bottom: 1.15rem;
    }

    .hero-shell::before {
        content: "";
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at 20% 8%, rgba(122,162,255,0.16), transparent 38%);
        pointer-events: none;
    }

    .hero-grid {
        display: grid;
        grid-template-columns: 1.45fr 0.8fr;
        gap: 1.2rem;
        align-items: stretch;
    }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.42rem;
        padding: 0.46rem 0.78rem;
        border-radius: 999px;
        background: rgba(122,162,255,0.10);
        border: 1px solid rgba(122,162,255,0.18);
        color: #d7e4ff;
        font-size: 0.76rem;
        font-weight: 800;
        margin-bottom: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .hero-title {
        font-size: clamp(2.55rem, 4vw, 4.15rem);
        line-height: 0.98;
        letter-spacing: -0.065em;
        margin: 0 0 0.85rem 0;
        font-weight: 950;
        color: #ffffff;
        max-width: 760px;
    }

    .brand-highlight {
        background: linear-gradient(90deg, #7aa2ff, #d7e4ff 68%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-sub {
        font-size: 1rem;
        line-height: 1.8;
        color: #c3cedb;
        max-width: 760px;
        margin-bottom: 1rem;
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 0.45rem;
    }

    .pill {
        padding: 0.58rem 0.88rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.045);
        border: 1px solid rgba(255,255,255,0.08);
        color: #eef4fb;
        font-size: 0.84rem;
        font-weight: 700;
    }

    .hero-stat-panel {
        height: 100%;
        border-radius: 26px;
        padding: 1.25rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.025));
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: var(--shadow-soft);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .hero-stat-kicker {
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 800;
        color: var(--soft);
        margin-bottom: 0.45rem;
    }

    .hero-stat-big {
        font-size: 2.55rem;
        font-weight: 950;
        letter-spacing: -0.05em;
        color: white;
        margin: 0 0 0.25rem 0;
    }

    .hero-stat-copy {
        font-size: 0.96rem;
        color: #c6d0dc;
        line-height: 1.75;
    }

    .mini-metrics {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
        margin-top: 1rem;
    }

    .mini-metric {
        border-radius: 18px;
        padding: 0.95rem;
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.08);
        transition: all 0.22s ease;
    }

    .mini-metric:hover {
        transform: translateY(-2px);
        border-color: rgba(122,162,255,0.22);
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
    .section-card,
    .download-card,
    .metric-card,
    .keyword-box,
    .suggestion-card,
    .empty-card {
        position: relative;
        overflow: hidden;
        background: linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.022));
        border: 1px solid var(--stroke);
        border-radius: var(--radius-xl);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: var(--shadow-soft);
        transition: all 0.22s ease;
    }

    .section-card:hover,
    .metric-card:hover,
    .keyword-box:hover,
    .suggestion-card:hover,
    .download-card:hover {
        transform: translateY(-3px);
        border-color: rgba(122,162,255,0.22);
        box-shadow: 0 22px 46px rgba(0,0,0,0.24);
    }

    .section-card,
    .download-card {
        padding: 1.55rem;
        margin-bottom: 1rem;
    }

    .empty-card {
        padding: 1.35rem;
        text-align: center;
        color: #9aa8bb;
        margin-top: 0.6rem;
    }

    .mini-step {
        display: inline-block;
        padding: 0.36rem 0.68rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 800;
        background: rgba(122,162,255,0.10);
        color: #d9e5ff;
        border: 1px solid rgba(122,162,255,0.18);
        margin-bottom: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .section-title {
        font-size: 1.32rem;
        font-weight: 900;
        margin-bottom: 0.22rem;
        color: white;
        letter-spacing: -0.03em;
    }

    .section-sub {
        color: #b8c4d2;
        font-size: 0.96rem;
        margin-bottom: 0;
        line-height: 1.7;
    }

    /* ---------------- Labels ---------------- */
    .stFileUploader label,
    .stTextArea label,
    .stRadio label,
    label {
        color: #f2f6fb !important;
        font-weight: 800 !important;
    }

    /* ---------------- File uploader ---------------- */
    div[data-testid="stFileUploader"] {
        border: 1px dashed rgba(255,255,255,0.14);
        border-radius: 22px;
        padding: 0.7rem;
        background: rgba(255,255,255,0.03);
        backdrop-filter: blur(14px);
    }

    div[data-testid="stFileUploader"] section {
        background: transparent !important;
    }

    /* ---------------- Text area ---------------- */
    div[data-testid="stTextArea"] textarea,
    .stTextArea textarea {
        border-radius: 20px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        background: linear-gradient(180deg, #f7f9fc, #f3f6fb) !important;
        color: #0f1728 !important;
        -webkit-text-fill-color: #0f1728 !important;
        padding: 1rem !important;
        min-height: 280px !important;
        box-shadow: none !important;
        font-weight: 500 !important;
        line-height: 1.68 !important;
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
        box-shadow: 0 0 0 4px rgba(122,162,255,0.16) !important;
        outline: none !important;
    }

    /* ---------------- Buttons ---------------- */
    .stButton > button,
    .stDownloadButton > button {
        width: 100%;
        border-radius: 18px !important;
        min-height: 3.1rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em;
        border: none !important;
        background: linear-gradient(135deg, #5d8dff, #7aa2ff) !important;
        color: white !important;
        box-shadow: 0 12px 28px rgba(91,140,255,0.28);
        transition: all 0.18s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-2px) scale(1.01);
        box-shadow: 0 16px 34px rgba(91,140,255,0.42);
        filter: brightness(1.03);
    }

    .stButton > button:active,
    .stDownloadButton > button:active {
        transform: translateY(0);
    }

    /* Secondary subtle buttons inside radios / utility actions if any */
    .ghost-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.72rem 1rem;
        border-radius: 16px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        color: white;
        font-weight: 700;
    }

    /* ---------------- Progress ---------------- */
    div[data-testid="stProgressBar"] {
        margin-bottom: 1rem;
    }

    div[data-testid="stProgressBar"] > div {
        background: rgba(255,255,255,0.08) !important;
        border-radius: 999px !important;
        overflow: hidden;
        height: 12px !important;
    }

    div[data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #7aa2ff, #5d8dff) !important;
        border-radius: 999px !important;
    }

    /* ---------------- Metrics ---------------- */
    .metric-card {
        padding: 1.1rem;
        border-radius: 22px;
    }

    [data-testid="metric-container"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    [data-testid="metric-container"] label {
        color: #9fb0c4 !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        font-size: 0.71rem !important;
    }

    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 2rem !important;
        font-weight: 950 !important;
        letter-spacing: -0.04em;
    }

    /* ---------------- Keyword boxes ---------------- */
    .keyword-box {
        padding: 1rem;
        min-height: 220px;
    }

    .keyword-title {
        font-weight: 850;
        margin-bottom: 0.8rem;
        font-size: 1rem;
        color: white;
    }

    .chip-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 0.52rem;
    }

    .chip-good {
        background: rgba(46,204,113,0.12);
        color: #d7fbe5;
        border: 1px solid rgba(46,204,113,0.24);
        padding: 0.42rem 0.72rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 800;
    }

    .chip-missing {
        background: rgba(245,158,11,0.12);
        color: #fdebc6;
        border: 1px solid rgba(245,158,11,0.24);
        padding: 0.42rem 0.72rem;
        border-radius: 999px;
        font-size: 0.84rem;
        font-weight: 800;
    }

    /* ---------------- Requirement items ---------------- */
    .req-item {
        padding: 0.9rem 1rem;
        border-radius: 16px;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 0.65rem;
        color: #dbe4ef;
        line-height: 1.65;
    }

    /* ---------------- Suggestion cards ---------------- */
    .suggestion-card {
        padding: 1.05rem;
        margin-bottom: 1rem;
    }

    .line-label {
        font-size: 0.77rem;
        color: #aeb9c7;
        font-weight: 800;
        margin-bottom: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    }

    .reason-box {
        background: rgba(122,162,255,0.08);
        border: 1px solid rgba(122,162,255,0.16);
        padding: 0.92rem 1rem;
        border-radius: 16px;
        color: #d7e4ff;
        margin-top: 0.8rem;
        margin-bottom: 0.95rem;
        line-height: 1.65;
    }

    /* Code blocks */
    div[data-testid="stCodeBlock"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(6,10,18,0.95) !important;
    }

    div[data-testid="stCodeBlock"] pre,
    div[data-testid="stCodeBlock"] code {
        white-space: pre-wrap !important;
        word-break: break-word !important;
        overflow-wrap: anywhere !important;
        font-size: 0.92rem !important;
        line-height: 1.6 !important;
    }

    details {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 0.38rem 0.75rem;
    }

    /* ---------------- RADIO ---------------- */
    div[data-testid="stRadio"] > div {
        gap: 0.7rem;
    }

    div[data-testid="stRadio"] label {
        color: #eef4fb !important;
    }

    div[role="radiogroup"] {
        gap: 0.8rem !important;
    }

    div[role="radiogroup"] > label {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 18px !important;
        padding: 0.96rem 1rem !important;
        margin-bottom: 0.72rem !important;
        transition: all 0.2s ease;
        display: flex !important;
        align-items: center !important;
        min-height: 64px !important;
    }

    div[role="radiogroup"] > label:hover {
        border-color: rgba(122,162,255,0.32) !important;
        background: rgba(122,162,255,0.05) !important;
        transform: translateY(-1px);
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

    /* Streamlit messages */
    div[data-baseweb="notification"] {
        border-radius: 18px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
    }

    /* Divider helper */
    .subtle-divider {
        height: 1px;
        width: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
        margin: 0.65rem 0 0.2rem;
    }

    .footer-note {
        text-align: center;
        color: #91a0b2;
        margin-top: 1.25rem;
        font-size: 0.9rem;
    }

    .success-banner {
        padding: 0.95rem 1rem;
        border-radius: 16px;
        background: rgba(46,204,113,0.10);
        border: 1px solid rgba(46,204,113,0.18);
        color: #d9fbe6;
        margin-bottom: 0.9rem;
    }

    @media (max-width: 1050px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }

        .hero-title {
            font-size: 2.85rem;
        }

        .topbar {
            flex-direction: column;
            align-items: flex-start;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


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


def full_reset() -> None:
    st.session_state.resume_processor = None
    st.session_state.ats_analysis = None
    st.session_state.suggestions = []
    st.session_state.choices_made = {}
    st.session_state.pdf_bytes = None
    st.session_state.tailored_docx_bytes = None
    st.session_state.uploaded_filename = None
    st.session_state.uploaded_file_signature = None


def show_empty_state(message: str) -> None:
    st.markdown(
        f"""
        <div class="empty-card">
            {message}
        </div>
        """,
        unsafe_allow_html=True,
    )
def extract_name_from_resume(lines):
    for line in lines:
        text = line["text"].strip()
        words = text.split()
        if len(words) >= 2:
            return f"{words[0]}_{words[1]}"
    return "Candidate"
import re

def extract_job_title(job_description):
    # Try first line or common patterns
    lines = job_description.strip().split("\n")
    
    for line in lines[:5]:
        line = line.strip()
        if len(line) < 80 and not line.lower().startswith(("about", "we", "company")):
            return re.sub(r'[^\w\s]', '', line).replace(" ", "_")
    
    return "Role"
    
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
st.markdown(
    """
<div class="topbar">
    <div class="brand">
        <div class="brand-badge">✦</div>
        <div>
            <div class="brand-title">Rizzume</div>
            <div class="brand-sub">Resume tailoring that feels sharp, polished, and recruiter-ready</div>
        </div>
    </div>
    <div class="topbar-right">
        <div class="status-pill">ATS Match</div>
        <div class="status-pill">Format Safe</div>
        <div class="status-pill">DOCX + PDF</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------
# HERO
# ---------------------------------------------------
st.markdown(
    """
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
                Spot keyword gaps, generate sharper rewrites, and export a cleaner final version with confidence.
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
                    Compare your resume against the role, find what is missing, and improve only the lines that matter most without destroying layout.
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
""",
    unsafe_allow_html=True,
)


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
st.markdown(
    """
<div class="section-card">
    <div class="mini-step">Step 01</div>
    <div class="section-title">Upload Resume and Job Description</div>
    <div class="section-sub">
        Start with your DOCX resume and the role you want to target.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1.35], gap="large")

with left:
    uploaded_file = st.file_uploader("Upload your resume (.docx only)", type=["docx"])

with right:
    job_description = st.text_area(
        "Paste Job Description",
        height=280,
        placeholder="Paste the full job description here...",
    )

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    current_signature = (uploaded_file.name, len(file_bytes))

    if st.session_state.uploaded_file_signature != current_signature:
        st.session_state.resume_processor = ResumeProcessor(file_bytes)
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.uploaded_file_signature = current_signature
        reset_state_for_new_file()
        st.toast("Resume uploaded successfully", icon="✅")
        st.markdown(
            '<div class="success-banner">Resume uploaded successfully. Ready to analyze and tailor.</div>',
            unsafe_allow_html=True,
        )

utility_col1, utility_col2, utility_col3 = st.columns([1, 1, 4], gap="large")
with utility_col1:
    if st.button("Analyze ATS Match", use_container_width=True):
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
            st.toast("Analyzing resume…", icon="⚡")
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

with utility_col2:
    if st.button("Reset", use_container_width=True):
        full_reset()
        st.toast("Workspace reset", icon="🧹")
        st.rerun()


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
if st.session_state.resume_processor is not None:
    st.markdown(
        """
    <div class="section-card">
        <div class="mini-step">Step 02</div>
        <div class="section-title">Analyze ATS Match</div>
        <div class="section-sub">
            See keyword coverage, missing terms, and key requirements before making edits.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

if not st.session_state.ats_analysis and st.session_state.resume_processor is not None:
    show_empty_state("Upload your resume and run analysis to unlock ATS score, keyword coverage, and rewrite suggestions ✦")


# ---------------------------------------------------
# ATS RESULTS
# ---------------------------------------------------
if st.session_state.ats_analysis:
    ats = st.session_state.ats_analysis
    ats_score = int(ats.get("ats_score", 0))

    confidence = "Low"
    if ats_score >= 80:
        confidence = "High"
    elif ats_score >= 60:
        confidence = "Medium"

    c1, c2, c3, c4 = st.columns(4, gap="large")
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
    with c4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Confidence", confidence)
        st.markdown('</div>', unsafe_allow_html=True)

    if ats.get("score_note"):
        st.info(ats.get("score_note"))

    kw1, kw2 = st.columns(2, gap="large")

    with kw1:
        present_keywords = ats.get("present_keywords", [])
        present_html = (
            "".join([f'<span class="chip-good">{kw}</span>' for kw in present_keywords])
            if present_keywords
            else '<span style="color:#9fb0c4;">No keywords detected.</span>'
        )

        st.markdown(
            f"""
        <div class="keyword-box">
            <div class="keyword-title">Present Keywords</div>
            <div class="chip-wrap">{present_html}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with kw2:
        missing_keywords = ats.get("missing_keywords", [])
        missing_html = (
            "".join([f'<span class="chip-missing">{kw}</span>' for kw in missing_keywords])
            if missing_keywords
            else '<span style="color:#9fb0c4;">No missing keywords detected.</span>'
        )

        st.markdown(
            f"""
        <div class="keyword-box">
            <div class="keyword-title">Missing Keywords</div>
            <div class="chip-wrap">{missing_html}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

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
        st.toast("Generating line rewrites…", icon="✨")
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
if st.session_state.ats_analysis and not st.session_state.suggestions:
    show_empty_state("Your ATS analysis is ready. Generate suggestions to review line-by-line rewrite options.")

if st.session_state.suggestions:
    st.markdown(
        """
    <div class="section-card">
        <div class="mini-step">Step 03</div>
        <div class="section-title">Choose Better Rewrites</div>
        <div class="section-sub">
            Review suggestions line by line and keep only the changes you want.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    total_suggestions = len(st.session_state.suggestions)
    selected_count = len(st.session_state.choices_made)

    st.progress(
        selected_count / total_suggestions if total_suggestions else 0,
        text=f"Selections made: {selected_count}/{total_suggestions}",
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
                unsafe_allow_html=True,
            )

        radio_options = ["Keep original"] + options
        current_value = st.session_state.choices_made.get(i, "Keep original")

        selected = st.radio(
            f"Choose best option for line {line_index}",
            radio_options,
            index=radio_options.index(current_value) if current_value in radio_options else 0,
            key=f"radio_{i}",
            label_visibility="collapsed",
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
                st.toast("Changes applied", icon="✅")
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
        '<div class="section-sub">Export your tailored DOCX, then generate a PDF once everything looks right.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="subtle-divider"></div>', unsafe_allow_html=True)

    current_docx_bytes = (
        st.session_state.tailored_docx_bytes
        if st.session_state.tailored_docx_bytes is not None
        else st.session_state.resume_processor.export()
    )

lines = st.session_state.resume_processor.get_all_lines()

name_part = extract_name_from_resume(lines)
job_part = extract_job_title(job_description)

file_stem = f"{name_part}_{job_part}_Resume"

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
                st.toast("Generating PDF…", icon="📄")
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
    '<div class="footer-note">Rizzume — tailor faster, keep formatting, and ship a cleaner application.</div>',
    unsafe_allow_html=True,
)
