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
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@400;500&display=swap');

    :root {
        --ink:       #0a0a0f;
        --ink2:      #13131a;
        --ink3:      #1c1c27;
        --border:    rgba(255,255,255,0.07);
        --border2:   rgba(255,255,255,0.12);
        --gold:      #c8a96e;
        --gold2:     #e8c98e;
        --cream:     #f5f0e8;
        --muted:     rgba(245,240,232,0.45);
        --muted2:    rgba(245,240,232,0.65);
        --green:     #3ecf8e;
        --orange:    #f5a623;
        --red:       #ff6b6b;
    }

    /* ── Reset ──────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background-color: var(--ink) !important;
        color: var(--cream);
    }

    .block-container {
        padding-top: 0 !important;
        padding-bottom: 3rem;
        max-width: 1280px;
    }

    /* hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ── Top wordmark bar ────────────────────────── */
    .rizzume-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.6rem 0 0.6rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 2.8rem;
    }

    .rizzume-wordmark {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.8rem;
        letter-spacing: 0.12em;
        color: var(--cream);
        line-height: 1;
    }

    .rizzume-wordmark span {
        color: var(--gold);
    }

    .rizzume-tag {
        font-size: 0.78rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--muted);
        padding: 0.38rem 0.9rem;
        border: 1px solid var(--border2);
        border-radius: 999px;
    }

    /* ── Hero section ────────────────────────────── */
    .hero-block {
        position: relative;
        overflow: hidden;
        background: var(--ink2);
        border: 1px solid var(--border2);
        border-radius: 20px;
        padding: 3rem 3rem 2.6rem 3rem;
        margin-bottom: 2.4rem;
    }

    .hero-block::before {
        content: "RIZZUME";
        font-family: 'Bebas Neue', sans-serif;
        font-size: 14rem;
        letter-spacing: 0.08em;
        position: absolute;
        right: -1.5rem;
        top: 50%;
        transform: translateY(-50%);
        color: rgba(200,169,110,0.04);
        pointer-events: none;
        line-height: 1;
        white-space: nowrap;
    }

    .hero-eyebrow {
        font-size: 0.72rem;
        letter-spacing: 0.3em;
        text-transform: uppercase;
        color: var(--gold);
        margin-bottom: 0.9rem;
    }

    .hero-headline {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 4rem;
        letter-spacing: 0.04em;
        line-height: 0.95;
        color: var(--cream);
        margin-bottom: 1.1rem;
    }

    .hero-headline em {
        color: var(--gold);
        font-style: normal;
    }

    .hero-body {
        font-size: 1.05rem;
        color: var(--muted2);
        font-weight: 300;
        max-width: 520px;
        line-height: 1.65;
        margin-bottom: 1.6rem;
    }

    .hero-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.42rem 0.85rem;
        border-radius: 999px;
        border: 1px solid var(--border2);
        background: rgba(255,255,255,0.03);
        font-size: 0.82rem;
        color: var(--muted2);
        letter-spacing: 0.02em;
    }

    .hero-pill::before {
        content: "◈";
        color: var(--gold);
        font-size: 0.65rem;
    }

    /* ── Progress track ──────────────────────────── */
    .progress-track {
        display: flex;
        align-items: center;
        gap: 0;
        margin-bottom: 2.8rem;
    }

    .p-step {
        flex: 1;
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.45rem;
    }

    .p-step:not(:last-child)::after {
        content: "";
        position: absolute;
        top: 16px;
        left: calc(50% + 16px);
        right: calc(-50% + 16px);
        height: 1px;
        background: var(--border2);
    }

    .p-dot {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: 1px solid var(--border2);
        background: var(--ink2);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        color: var(--muted);
        font-family: 'DM Mono', monospace;
        font-weight: 500;
        transition: all 0.3s;
        position: relative;
        z-index: 1;
    }

    .p-dot.active {
        background: var(--gold);
        border-color: var(--gold);
        color: var(--ink);
        font-weight: 700;
        box-shadow: 0 0 18px rgba(200,169,110,0.4);
    }

    .p-dot.done {
        background: transparent;
        border-color: var(--gold);
        color: var(--gold);
    }

    .p-label {
        font-size: 0.72rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--muted);
        text-align: center;
    }

    .p-label.active { color: var(--gold); }

    /* ── Step cards ──────────────────────────────── */
    .step-header {
        display: flex;
        align-items: baseline;
        gap: 1rem;
        margin-bottom: 1.4rem;
    }

    .step-num {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 1.1rem;
        letter-spacing: 0.18em;
        color: var(--gold);
        border: 1px solid rgba(200,169,110,0.35);
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        flex-shrink: 0;
    }

    .step-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2rem;
        letter-spacing: 0.06em;
        color: var(--cream);
        line-height: 1;
    }

    .step-divider {
        width: 100%;
        height: 1px;
        background: linear-gradient(90deg, var(--gold) 0%, transparent 60%);
        margin-bottom: 1.6rem;
        opacity: 0.35;
    }

    /* ── Metric tiles ────────────────────────────── */
    .metric-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin-bottom: 1.6rem;
    }

    .metric-tile {
        background: var(--ink2);
        border: 1px solid var(--border2);
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        position: relative;
        overflow: hidden;
    }

    .metric-tile::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--gold), transparent);
    }

    .metric-label {
        font-size: 0.7rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.5rem;
    }

    .metric-value {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.8rem;
        letter-spacing: 0.05em;
        line-height: 1;
        color: var(--cream);
    }

    .metric-value.gold { color: var(--gold); }
    .metric-value.green { color: var(--green); }
    .metric-value.orange { color: var(--orange); }

    /* ── Keyword grids ───────────────────────────── */
    .kw-panel {
        background: var(--ink2);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 1.4rem;
        min-height: 200px;
    }

    .kw-panel-title {
        font-size: 0.72rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 1rem;
    }

    .chip-wrap { display: flex; flex-wrap: wrap; gap: 0.45rem; }

    .chip {
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 500;
        letter-spacing: 0.01em;
    }

    .chip-present {
        background: rgba(62,207,142,0.1);
        color: var(--green);
        border: 1px solid rgba(62,207,142,0.25);
    }

    .chip-missing {
        background: rgba(245,166,35,0.1);
        color: var(--orange);
        border: 1px solid rgba(245,166,35,0.25);
    }

    /* ── Requirements list ───────────────────────── */
    .req-item {
        display: flex;
        align-items: flex-start;
        gap: 0.7rem;
        padding: 0.75rem 1rem;
        background: var(--ink2);
        border: 1px solid var(--border);
        border-radius: 12px;
        margin-bottom: 0.5rem;
        color: var(--muted2);
        font-size: 0.93rem;
        line-height: 1.5;
    }

    .req-item::before {
        content: "—";
        color: var(--gold);
        flex-shrink: 0;
        margin-top: 0.05rem;
    }

    /* ── Suggestion cards ────────────────────────── */
    .sug-card {
        background: var(--ink2);
        border: 1px solid var(--border2);
        border-radius: 18px;
        padding: 1.4rem 1.5rem;
        margin-bottom: 1.2rem;
        position: relative;
        overflow: hidden;
    }

    .sug-card::before {
        content: "";
        position: absolute;
        left: 0; top: 0; bottom: 0;
        width: 3px;
        background: linear-gradient(180deg, var(--gold), transparent);
        border-radius: 3px 0 0 3px;
    }

    .sug-line-label {
        font-size: 0.68rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--gold);
        margin-bottom: 0.6rem;
    }

    .sug-reason {
        background: rgba(200,169,110,0.06);
        border-left: 2px solid rgba(200,169,110,0.3);
        border-radius: 0 10px 10px 0;
        padding: 0.7rem 1rem;
        color: var(--muted2);
        font-size: 0.88rem;
        line-height: 1.55;
        margin: 0.7rem 0 0.9rem 0;
    }

    /* ── Download block ──────────────────────────── */
    .dl-block {
        background: var(--ink2);
        border: 1px solid var(--border2);
        border-radius: 20px;
        padding: 2rem 2.2rem;
        position: relative;
        overflow: hidden;
        margin-top: 2rem;
    }

    .dl-block::after {
        content: "◈";
        font-size: 18rem;
        position: absolute;
        right: -3rem;
        top: 50%;
        transform: translateY(-50%);
        color: rgba(200,169,110,0.03);
        pointer-events: none;
        line-height: 1;
    }

    .dl-title {
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.2rem;
        letter-spacing: 0.08em;
        color: var(--cream);
        margin-bottom: 0.3rem;
    }

    .dl-sub {
        color: var(--muted);
        font-size: 0.9rem;
        margin-bottom: 1.4rem;
    }

    /* ── Streamlit overrides ─────────────────────── */

    /* Buttons */
    .stButton > button {
        background: transparent !important;
        border: 1px solid var(--border2) !important;
        color: var(--cream) !important;
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em !important;
        padding: 0.55rem 1.2rem !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        background: var(--gold) !important;
        border-color: var(--gold) !important;
        color: var(--ink) !important;
    }

    .stButton > button:focus {
        box-shadow: 0 0 0 2px rgba(200,169,110,0.4) !important;
    }

    /* Primary buttons */
    .stButton > button[kind="primary"] {
        background: var(--gold) !important;
        border-color: var(--gold) !important;
        color: var(--ink) !important;
        font-weight: 700 !important;
    }

    /* Download buttons */
    .stDownloadButton > button {
        background: transparent !important;
        border: 1px solid var(--gold) !important;
        color: var(--gold) !important;
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em !important;
        transition: all 0.2s ease !important;
    }

    .stDownloadButton > button:hover {
        background: var(--gold) !important;
        color: var(--ink) !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: var(--ink2) !important;
        border: 1px dashed rgba(200,169,110,0.3) !important;
        border-radius: 16px !important;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--gold) !important;
    }

    [data-testid="stFileUploaderDropzoneInstructions"] p {
        color: var(--muted) !important;
    }

    /* Text area */
    [data-testid="stTextArea"] textarea {
        background: var(--ink2) !important;
        border: 1px solid var(--border2) !important;
        border-radius: 14px !important;
        color: var(--cream) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.92rem !important;
    }

    [data-testid="stTextArea"] textarea:focus {
        border-color: var(--gold) !important;
        box-shadow: 0 0 0 2px rgba(200,169,110,0.15) !important;
    }

    [data-testid="stTextArea"] textarea::placeholder {
        color: var(--muted) !important;
    }

    /* Code blocks */
    [data-testid="stCodeBlock"] {
        background: var(--ink3) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }

    [data-testid="stCodeBlock"] pre {
        color: rgba(232,201,142,0.8) !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.84rem !important;
    }

    /* Expander */
    [data-testid="stExpander"] {
        background: var(--ink2) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
    }

    [data-testid="stExpander"] summary {
        color: var(--muted2) !important;
        font-size: 0.9rem !important;
    }

    /* Radio buttons */
    .stRadio > div {
        gap: 0.5rem !important;
    }

    .stRadio label {
        color: var(--muted2) !important;
        font-size: 0.92rem !important;
    }

    /* Progress bar */
    .stProgress > div > div {
        background: var(--ink3) !important;
        border-radius: 999px !important;
    }

    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--gold), var(--gold2)) !important;
        border-radius: 999px !important;
    }

    .stProgress p {
        color: var(--muted) !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.05em !important;
    }

    /* Alerts */
    .stAlert {
        background: var(--ink2) !important;
        border-radius: 14px !important;
        border: 1px solid var(--border2) !important;
    }

    /* Metric widget */
    [data-testid="stMetric"] {
        background: var(--ink2);
        border: 1px solid var(--border2);
        border-radius: 14px;
        padding: 1rem;
    }

    [data-testid="stMetricValue"] {
        color: var(--gold) !important;
        font-family: 'Bebas Neue', sans-serif !important;
        font-size: 2.4rem !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.15em !important;
        text-transform: uppercase !important;
    }

    /* Columns gap */
    [data-testid="stHorizontalBlock"] {
        gap: 1.2rem;
    }

    /* Subheader */
    h3 {
        font-family: 'Bebas Neue', sans-serif !important;
        letter-spacing: 0.1em !important;
        color: var(--cream) !important;
        font-size: 1.6rem !important;
    }

    /* Caption / info */
    .stInfo {
        background: rgba(200,169,110,0.07) !important;
        border: 1px solid rgba(200,169,110,0.2) !important;
        border-radius: 12px !important;
        color: var(--gold2) !important;
    }

    .stWarning {
        background: rgba(245,166,35,0.08) !important;
        border: 1px solid rgba(245,166,35,0.25) !important;
        border-radius: 12px !important;
    }

    .stSuccess {
        background: rgba(62,207,142,0.07) !important;
        border: 1px solid rgba(62,207,142,0.2) !important;
        border-radius: 12px !important;
        color: var(--green) !important;
    }

    .stError {
        background: rgba(255,107,107,0.07) !important;
        border: 1px solid rgba(255,107,107,0.25) !important;
        border-radius: 12px !important;
    }

    /* Spacing helpers */
    .spacer-sm { height: 0.8rem; }
    .spacer-md { height: 1.4rem; }
    .spacer-lg { height: 2.2rem; }

    .footer-note {
        text-align: center;
        color: var(--muted);
        margin-top: 2rem;
        font-size: 0.82rem;
        letter-spacing: 0.04em;
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
            ["soffice", "--headless", "--convert-to", "pdf", input_docx, "--outdir", tmpdir],
            capture_output=True, text=True, check=False,
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
# WORDMARK BAR
# ---------------------------------------------------
st.markdown("""
<div class="rizzume-topbar">
    <div class="rizzume-wordmark">RIZ<span>ZUME</span></div>
    <div class="rizzume-tag">Resume Intelligence ◈ AI-Powered</div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------
# HERO
# ---------------------------------------------------
st.markdown("""
<div class="hero-block">
    <div class="hero-eyebrow">◈ &nbsp; Next-gen resume tailoring</div>
    <div class="hero-headline">Make Your<br>Resume <em>Irresistible</em></div>
    <div class="hero-body">
        Match any job description with surgical precision.
        Format-safe rewrites, ATS scoring, and export-ready output —
        without breaking a single line of formatting.
    </div>
    <div class="hero-pills">
        <div class="hero-pill">ATS Match Scoring</div>
        <div class="hero-pill">Format-Safe Rewrites</div>
        <div class="hero-pill">Multiple Options per Line</div>
        <div class="hero-pill">DOCX + PDF Export</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------
# PROGRESS TRACK
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

steps_meta = [
    ("01", "Upload"),
    ("02", "Analyze"),
    ("03", "Rewrite"),
    ("04", "Export"),
]

dots_html = ""
for i, (num, label) in enumerate(steps_meta):
    step_num = i + 1
    dot_class = "active" if step_num == progress_steps + 1 else ("done" if step_num <= progress_steps else "")
    label_class = "active" if step_num <= progress_steps + 1 else ""
    check = "✓" if step_num <= progress_steps else num
    dots_html += f"""
    <div class="p-step">
        <div class="p-dot {dot_class}">{check}</div>
        <div class="p-label {label_class}">{label}</div>
    </div>
    """

st.markdown(f'<div class="progress-track">{dots_html}</div>', unsafe_allow_html=True)


# ---------------------------------------------------
# STEP 1 — INPUTS
# ---------------------------------------------------
st.markdown("""
<div class="step-header">
    <div class="step-num">STEP 01</div>
    <div class="step-title">Upload & Describe</div>
</div>
<div class="step-divider"></div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 1.45], gap="large")

with left:
    uploaded_file = st.file_uploader("Upload your resume (.docx only)", type=["docx"])

with right:
    job_description = st.text_area(
        "Paste Job Description",
        height=220,
        placeholder="Paste the full job description here — include requirements, responsibilities, and preferred skills..."
    )

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    current_signature = (uploaded_file.name, len(file_bytes))

    if st.session_state.uploaded_file_signature != current_signature:
        st.session_state.resume_processor = ResumeProcessor(file_bytes)
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.uploaded_file_signature = current_signature
        reset_state_for_new_file()
        st.success(f"◈ Resume loaded — {uploaded_file.name}")

if st.session_state.resume_processor is not None:
    with st.expander("Preview extracted resume lines"):
        lines = st.session_state.resume_processor.get_all_lines()
        for line in lines:
            if line["text"].strip():
                st.write(f'**[{line["index"]}]** · {line["char_count"]} chars')
                st.code(line["text"])

st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)


# ---------------------------------------------------
# STEP 2 — ATS ANALYSIS
# ---------------------------------------------------
st.markdown("""
<div class="step-header">
    <div class="step-num">STEP 02</div>
    <div class="step-title">ATS Analysis</div>
</div>
<div class="step-divider"></div>
""", unsafe_allow_html=True)

analyze_col, _ = st.columns([1, 3])
with analyze_col:
    analyze_clicked = st.button("◈ Run ATS Analysis", use_container_width=True)

if analyze_clicked:
    if st.session_state.resume_processor is None:
        st.warning("Upload a resume first.")
    elif not job_description.strip():
        st.warning("Paste a job description first.")
    else:
        resume_text = "\n".join(
            line["text"]
            for line in st.session_state.resume_processor.get_all_lines()
            if line["text"].strip()
        )
        with st.spinner("Scoring your resume against the job description..."):
            try:
                ats_analysis = client.analyze_ats(resume_text, job_description)
                st.session_state.ats_analysis = ats_analysis
                st.session_state.suggestions = []
                st.session_state.choices_made = {}
                st.session_state.tailored_docx_bytes = None
                st.session_state.pdf_bytes = None
                st.success("Analysis complete.")
            except Exception as e:
                st.error(f"Analysis failed: {e}")

if st.session_state.ats_analysis:
    ats = st.session_state.ats_analysis
    ats_score = int(ats.get("ats_score", 0))

    # Score colour
    score_colour = "green" if ats_score >= 70 else ("gold" if ats_score >= 45 else "orange")

    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown(f"""
        <div class="metric-tile">
            <div class="metric-label">ATS Score</div>
            <div class="metric-value {score_colour}">{ats_score}%</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-tile">
            <div class="metric-label">Present Keywords</div>
            <div class="metric-value green">{len(ats.get('present_keywords', []))}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-tile">
            <div class="metric-label">Missing Keywords</div>
            <div class="metric-value orange">{len(ats.get('missing_keywords', []))}</div>
        </div>""", unsafe_allow_html=True)

    if ats.get("score_note"):
        st.info(ats.get("score_note"))

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    kw1, kw2 = st.columns(2, gap="large")
    with kw1:
        present = ats.get("present_keywords", [])
        chips = "".join([f'<span class="chip chip-present">{kw}</span>' for kw in present]) \
            if present else '<span style="color:var(--muted)">None detected.</span>'
        st.markdown(f"""
        <div class="kw-panel">
            <div class="kw-panel-title">◈ Present Keywords</div>
            <div class="chip-wrap">{chips}</div>
        </div>""", unsafe_allow_html=True)

    with kw2:
        missing = ats.get("missing_keywords", [])
        chips = "".join([f'<span class="chip chip-missing">{kw}</span>' for kw in missing]) \
            if missing else '<span style="color:var(--muted)">None missing — great job.</span>'
        st.markdown(f"""
        <div class="kw-panel">
            <div class="kw-panel-title">◈ Missing Keywords</div>
            <div class="chip-wrap">{chips}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
    st.markdown("### Key Requirements")
    for req in ats.get("key_requirements", []):
        st.markdown(f'<div class="req-item">{req}</div>', unsafe_allow_html=True)

    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
    gen_col, _ = st.columns([1, 3])
    with gen_col:
        generate_clicked = st.button("◈ Generate Rewrites", use_container_width=True)

    if generate_clicked:
        lines = st.session_state.resume_processor.get_all_lines()
        with st.spinner("Crafting targeted rewrites for your resume..."):
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
                    st.success(f"{len(suggestions)} rewrite suggestion(s) ready.")
                else:
                    st.warning("No suggestions returned. Try a different job description.")
            except Exception as e:
                st.error(f"Suggestion generation failed: {e}")

st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)


# ---------------------------------------------------
# STEP 3 — CHOOSE REWRITES
# ---------------------------------------------------
if st.session_state.suggestions:
    st.markdown("""
    <div class="step-header">
        <div class="step-num">STEP 03</div>
        <div class="step-title">Choose Rewrites</div>
    </div>
    <div class="step-divider"></div>
    """, unsafe_allow_html=True)

    total_sug = len(st.session_state.suggestions)
    selected_ct = len(st.session_state.choices_made)
    st.progress(
        selected_ct / total_sug if total_sug else 0,
        text=f"Selections: {selected_ct} / {total_sug}"
    )
    st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

    for i, suggestion in enumerate(st.session_state.suggestions):
        line_index = suggestion.get("line_index", "?")
        original = suggestion.get("original", "")
        options = suggestion.get("options", [])
        reason = suggestion.get("reason", "")

        st.markdown(f"""
        <div class="sug-card">
            <div class="sug-line-label">◈ Line {line_index}</div>
        </div>
        """, unsafe_allow_html=True)

        st.code(original, language=None)

        if reason:
            st.markdown(f'<div class="sug-reason"><strong style="color:var(--gold)">Why rewrite:</strong> {reason}</div>', unsafe_allow_html=True)

        radio_options = ["Keep original"] + options
        current_value = st.session_state.choices_made.get(i, "Keep original")

        selected = st.radio(
            f"Choose for line {line_index}",
            radio_options,
            index=radio_options.index(current_value) if current_value in radio_options else 0,
            key=f"radio_{i}",
            label_visibility="collapsed"
        )

        if selected == "Keep original":
            st.session_state.choices_made.pop(i, None)
        else:
            st.session_state.choices_made[i] = selected

    st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
    apply_col, _ = st.columns([1, 3])
    with apply_col:
        apply_clicked = st.button("◈ Apply Selected Changes", use_container_width=True)

    if apply_clicked:
        processor = st.session_state.resume_processor
        if processor is None:
            st.error("Resume processor missing. Please re-upload your file.")
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
                st.success("Selected changes applied. Your tailored resume is ready to export.")
            except Exception as e:
                st.error(f"Failed to apply changes: {e}")

    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)


# ---------------------------------------------------
# STEP 4 — EXPORT
# ---------------------------------------------------
if st.session_state.resume_processor is not None:
    st.markdown("""
    <div class="step-header">
        <div class="step-num">STEP 04</div>
        <div class="step-title">Export</div>
    </div>
    <div class="step-divider"></div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="dl-block">
        <div class="dl-title">Download Your Tailored Resume</div>
        <div class="dl-sub">Export the finalized version as DOCX or convert to PDF.</div>
    </div>
    """, unsafe_allow_html=True)

    current_docx_bytes = (
        st.session_state.tailored_docx_bytes
        if st.session_state.tailored_docx_bytes is not None
        else st.session_state.resume_processor.export()
    )
    file_stem = get_file_stem(st.session_state.uploaded_filename or "resume.docx")

    d1, d2, d3 = st.columns([1, 1, 2], gap="large")

    with d1:
        st.download_button(
            label="↓ Download DOCX",
            data=current_docx_bytes,
            file_name=f"{file_stem}_rizzume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    with d2:
        if SOFFICE_AVAILABLE:
            if st.button("◈ Generate PDF", use_container_width=True):
                with st.spinner("Converting..."):
                    try:
                        st.session_state.pdf_bytes = convert_docx_to_pdf_bytes(current_docx_bytes)
                        st.success("PDF ready.")
                    except Exception as e:
                        st.error(f"PDF conversion failed: {e}")
        else:
            st.caption("PDF unavailable on this deployment.")

    with d3:
        if st.session_state.pdf_bytes is not None:
            st.download_button(
                label="↓ Download PDF",
                data=st.session_state.pdf_bytes,
                file_name=f"{file_stem}_rizzume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

st.markdown(
    '<div class="footer-note">Rizzume ◈ Format-safe, ATS-optimized, built to impress.</div>',
    unsafe_allow_html=True
)
