"""
app.py  —  Rizzume v2
Professional Resume Tailor · ATS Maximizer · Layout-Safe DOCX Export
"""
import os
import re
import shutil
import subprocess
import tempfile

import streamlit as st

# ─── PAGE CONFIG (must be first) ─────────────────────────────────────────────
st.set_page_config(
    page_title="Rizzume",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#05080f; --surface:#0b1120; --card:#0f1929;
  --border:rgba(255,255,255,0.09); --border2:rgba(255,255,255,0.16);
  --text:#e8edf5; --muted:#8a96a8; --subtle:#5a6373;
  --accent:#4f8bff; --accent2:#7ba7ff;
  --green:#22c55e; --amber:#f59e0b; --red:#ef4444;
  --font-head:'Syne',sans-serif; --font-body:'DM Sans',sans-serif;
  --font-mono:'JetBrains Mono',monospace;
  --r-sm:10px; --r-md:16px; --r-lg:22px; --r-xl:28px;
  --shadow:0 20px 60px rgba(0,0,0,0.45);
}
html,body,[class*="css"]{font-family:var(--font-body)!important;color:var(--text)!important;background:var(--bg)!important;}
.stApp{
  background:radial-gradient(ellipse 80% 60% at 15% 5%,rgba(79,139,255,0.14) 0%,transparent 55%),
             radial-gradient(ellipse 60% 50% at 88% 90%,rgba(79,139,255,0.09) 0%,transparent 55%),#05080f!important;
  min-height:100vh;
}
/* Login narrow container */
.block-container{max-width:480px!important;padding-top:0!important;padding-bottom:2rem!important;padding-left:1rem!important;padding-right:1rem!important;margin:0 auto!important;}
header[data-testid="stHeader"]{display:none!important;}
section[data-testid="stSidebar"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
footer{display:none!important;}
/* Login card */
.lcard{margin-top:max(6vh,2.5rem);border-radius:28px;padding:2.5rem 2rem 2rem;
  background:linear-gradient(160deg,rgba(255,255,255,0.058),rgba(255,255,255,0.02));
  border:1px solid rgba(255,255,255,0.08);
  box-shadow:0 40px 100px rgba(0,0,0,0.55),inset 0 1px 0 rgba(255,255,255,0.05);text-align:center;}
.lmark{width:54px;height:54px;margin:0 auto 1.3rem;border-radius:16px;display:flex;align-items:center;justify-content:center;
  background:linear-gradient(135deg,rgba(79,139,255,0.24),rgba(79,139,255,0.07));
  border:1px solid rgba(79,139,255,0.30);box-shadow:0 8px 28px rgba(79,139,255,0.20);font-size:1.45rem;color:#fff;}
.ltitle{font-family:var(--font-head);font-size:2.1rem;font-weight:800;letter-spacing:-0.07em;color:#fff;line-height:1;margin-bottom:0.5rem;}
.lsub{font-size:0.87rem;color:#5d7290;line-height:1.6;margin-bottom:1.4rem;}
.ldivider{height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.07),transparent);margin-bottom:1.5rem;}
.alabel{display:block;text-align:left;font-size:0.7rem;color:#4a6080;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:0.35rem;margin-top:0.85rem;}
.lnote{margin-top:1.3rem;text-align:center;font-size:0.74rem;color:#2a3a4d;letter-spacing:0.03em;}
/* Inputs */
div[data-testid="stTextInput"] input{border-radius:14px!important;min-height:3rem!important;background:rgba(255,255,255,0.038)!important;border:1px solid rgba(255,255,255,0.08)!important;color:#edf3fb!important;box-shadow:none!important;padding-left:1rem!important;font-size:0.94rem!important;}
div[data-testid="stTextInput"] input:focus{border-color:rgba(79,139,255,0.48)!important;box-shadow:0 0 0 3px rgba(79,139,255,0.1)!important;}
div[data-testid="stTextInput"] input::placeholder{color:#2d3d52!important;opacity:1!important;}
div[data-testid="stTextInput"] label{display:none!important;}
div[data-testid="stFormSubmitButton"]>button{width:100%!important;border-radius:14px!important;min-height:3.1rem!important;margin-top:1.2rem!important;font-family:var(--font-body)!important;font-weight:700!important;font-size:0.95rem!important;border:none!important;background:linear-gradient(135deg,#2e62d9,#5590ff)!important;color:#fff!important;box-shadow:0 8px 28px rgba(79,139,255,0.22)!important;}
</style>
""", unsafe_allow_html=True)

# ─── PASSWORD GATE ────────────────────────────────────────────────────────────
def check_password():
    if st.session_state.get("_auth"):
        return True

    def _authenticate():
        if st.session_state.get("pw_input", "") == st.secrets.get("APP_PASSWORD", ""):
            st.session_state["_auth"] = True
            st.session_state["_auth_fail"] = False
            st.rerun()
        else:
            st.session_state["_auth_fail"] = True

    st.markdown('<div class="lcard"><div class="lmark">✦</div><div class="ltitle">Rizzume</div><div class="lsub">ATS Resume Tailor</div><div class="ldivider"></div></div>', unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False, enter_to_submit=True):
        st.markdown('<span class="alabel">Password</span>', unsafe_allow_html=True)
        st.text_input("Password", type="password", key="pw_input", label_visibility="collapsed", placeholder="••••••••••")
        if st.form_submit_button("Enter Workspace  ✦", use_container_width=True):
            _authenticate()
    if st.session_state.get("_auth_fail"):
        st.error("Incorrect password. Please try again.")
    st.markdown('<div class="lnote">Private workspace · Authorized access only</div>', unsafe_allow_html=True)
    return False

if not check_password():
    st.stop()

# ─── RESTORE FULL-WIDTH LAYOUT ────────────────────────────────────────────────
st.markdown("""
<style>
.block-container{max-width:100%!important;padding:1rem 1.5rem!important;}
header[data-testid="stHeader"]{display:block!important;background:transparent!important;}
div[data-testid="stTextArea"] textarea{
  border-radius:16px!important;border:1px solid rgba(255,255,255,0.14)!important;
  background:#f7f9fc!important;color:#0d1422!important;-webkit-text-fill-color:#0d1422!important;
  caret-color:#0d1422!important;padding:1rem!important;min-height:280px!important;
  font-family:var(--font-body)!important;font-size:0.96rem!important;line-height:1.72!important;box-shadow:none!important;}
div[data-testid="stTextArea"] textarea::placeholder{color:#7a8694!important;opacity:1!important;}
div[data-testid="stTextArea"] textarea:focus{border-color:rgba(79,139,255,0.5)!important;box-shadow:0 0 0 4px rgba(79,139,255,0.14)!important;}
div[data-testid="stTextInput"] input{
  border-radius:14px!important;min-height:3rem!important;background:#f8fafc!important;
  border:1px solid rgba(15,23,42,0.14)!important;color:#0f172a!important;
  -webkit-text-fill-color:#0f172a!important;caret-color:#0f172a!important;
  box-shadow:none!important;padding-left:1rem!important;font-size:0.95rem!important;}
div[data-testid="stTextInput"] input:focus{border-color:rgba(79,139,255,0.45)!important;box-shadow:0 0 0 3px rgba(79,139,255,0.12)!important;}
div[data-testid="stTextInput"] label{display:none!important;}
.stButton>button,.stDownloadButton>button{
  width:100%!important;border-radius:var(--r-md)!important;min-height:3rem!important;
  font-family:var(--font-body)!important;font-weight:700!important;font-size:0.96rem!important;
  border:none!important;background:linear-gradient(135deg,#3a74f0,#5d95ff)!important;
  color:#fff!important;box-shadow:0 10px 28px rgba(79,139,255,0.28);transition:all 0.18s ease!important;}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px)!important;filter:brightness(1.05)!important;}
div[data-testid="stFileUploader"]{border:1.5px dashed rgba(255,255,255,0.14)!important;border-radius:var(--r-lg)!important;padding:0.6rem!important;background:rgba(255,255,255,0.025)!important;}
label{font-family:var(--font-body)!important;color:#dde5f0!important;font-weight:600!important;font-size:0.95rem!important;}
div[role="radiogroup"]>label{
  background:rgba(255,255,255,0.03)!important;border:1px solid var(--border)!important;
  border-radius:var(--r-md)!important;padding:0.9rem 1rem!important;margin-bottom:0.5rem!important;
  transition:all 0.18s ease!important;cursor:pointer!important;}
div[role="radiogroup"]>label:hover{border-color:rgba(79,139,255,0.34)!important;background:rgba(79,139,255,0.05)!important;}
div[role="radiogroup"]>label p,div[role="radiogroup"]>label span,div[role="radiogroup"]>label div{color:#dce8f5!important;font-family:var(--font-body)!important;font-size:0.94rem!important;line-height:1.6!important;}
/* Topbar */
.topbar{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:0.85rem 1.2rem;border-radius:var(--r-lg);margin-bottom:1.2rem;background:rgba(11,17,32,0.85);border:1px solid var(--border);backdrop-filter:blur(18px);position:sticky;top:0.5rem;z-index:100;box-shadow:0 8px 24px rgba(0,0,0,0.3);}
.brand{display:flex;align-items:center;gap:0.9rem;}
.brand-dot{width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,rgba(79,139,255,0.25),rgba(79,139,255,0.07));border:1px solid rgba(79,139,255,0.28);display:flex;align-items:center;justify-content:center;font-size:1.15rem;color:#fff;font-weight:900;}
.brand-name{font-family:var(--font-head);font-size:1.15rem;font-weight:800;color:#fff;letter-spacing:-0.04em;}
.brand-tagline{font-size:0.8rem;color:var(--muted);margin-top:0.08rem;}
.tpill{padding:0.44rem 0.76rem;border-radius:999px;background:rgba(255,255,255,0.04);border:1px solid var(--border);color:#c8d4e3;font-size:0.76rem;font-weight:600;}
.topbar-pills{display:flex;gap:0.5rem;flex-wrap:wrap;}
/* Cards */
.sec-card{border-radius:var(--r-xl);padding:1.5rem 1.6rem;background:linear-gradient(160deg,rgba(255,255,255,0.046),rgba(255,255,255,0.018));border:1px solid var(--border);margin-bottom:1rem;box-shadow:0 12px 35px rgba(0,0,0,0.2);}
.step-tag{display:inline-block;padding:0.3rem 0.62rem;border-radius:999px;background:rgba(79,139,255,0.1);border:1px solid rgba(79,139,255,0.2);color:#c5daff;font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.09em;margin-bottom:0.7rem;}
.sec-title{font-family:var(--font-head);font-size:1.3rem;font-weight:700;color:#fff;letter-spacing:-0.03em;margin-bottom:0.2rem;}
.sec-sub{font-size:0.94rem;color:#9aacbf;line-height:1.72;}
/* Metrics */
.metric-shell{border-radius:var(--r-lg);padding:1.1rem 1.15rem;background:rgba(255,255,255,0.04);border:1px solid var(--border);}
[data-testid="metric-container"]{background:transparent!important;border:none!important;padding:0!important;}
[data-testid="metric-container"] label{font-family:var(--font-body)!important;color:var(--muted)!important;font-weight:700!important;font-size:0.7rem!important;text-transform:uppercase;letter-spacing:0.09em;}
[data-testid="metric-container"] [data-testid="stMetricValue"]{font-family:var(--font-head)!important;color:#fff!important;font-size:2.1rem!important;font-weight:800!important;letter-spacing:-0.04em!important;}
/* Keywords */
.kw-box{border-radius:var(--r-lg);padding:1.05rem 1.1rem;background:rgba(255,255,255,0.03);border:1px solid var(--border);min-height:120px;margin-bottom:0.8rem;}
.kw-title{font-weight:700;font-size:0.97rem;color:#e2eaf4;margin-bottom:0.75rem;}
.chip-row{display:flex;flex-wrap:wrap;gap:0.48rem;}
.chip-ok{background:rgba(34,197,94,0.12);color:#bbf7d0;border:1px solid rgba(34,197,94,0.24);padding:0.38rem 0.68rem;border-radius:999px;font-size:0.82rem;font-weight:600;}
.chip-miss{background:rgba(245,158,11,0.12);color:#fde68a;border:1px solid rgba(245,158,11,0.24);padding:0.38rem 0.68rem;border-radius:999px;font-size:0.82rem;font-weight:600;}
.chip-placed{background:rgba(79,139,255,0.12);color:#bcd4ff;border:1px solid rgba(79,139,255,0.24);padding:0.38rem 0.68rem;border-radius:999px;font-size:0.82rem;font-weight:600;}
/* Suggestion cards */
.sug-card{border-radius:var(--r-lg);padding:1.1rem 1.15rem;margin-bottom:0.9rem;background:rgba(255,255,255,0.03);border:1px solid var(--border);}
.line-label{font-size:0.73rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:0.09em;margin-bottom:0.42rem;}
.reason-box{background:rgba(79,139,255,0.08);border:1px solid rgba(79,139,255,0.18);border-radius:12px;padding:0.7rem 0.9rem;color:#c8daff;margin:0.6rem 0;font-size:0.9rem;line-height:1.6;}
.kw-badge-row{display:flex;flex-wrap:wrap;gap:0.35rem;margin-top:0.5rem;}
.kw-badge{background:rgba(79,139,255,0.14);color:#bcd4ff;border:1px solid rgba(79,139,255,0.22);padding:0.25rem 0.52rem;border-radius:999px;font-size:0.76rem;font-weight:600;}
/* Progress bar */
.load-wrap{margin:0.5rem 0 1.2rem;}
.load-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;}
.load-label{font-size:0.86rem;font-weight:600;color:var(--muted);}
.load-pct{font-family:var(--font-head);font-size:1.1rem;font-weight:800;color:var(--accent2);letter-spacing:-0.03em;}
.load-track{width:100%;height:8px;border-radius:999px;background:rgba(255,255,255,0.07);overflow:hidden;}
.load-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#3a74f0,#6fa8ff);transition:width 0.5s cubic-bezier(.4,0,.2,1);box-shadow:0 0 12px rgba(79,139,255,0.5);}
/* Line editor */
.editor-wrap{border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;margin-bottom:1rem;}
.editor-header{background:#1a2236;padding:0.65rem 1.1rem;border-bottom:1px solid rgba(255,255,255,0.07);}
.req-item{padding:0.85rem 1rem;border-radius:var(--r-sm);background:rgba(255,255,255,0.03);border:1px solid var(--border);color:#cdd8e7;font-size:0.94rem;line-height:1.68;margin-bottom:0.6rem;}
/* Export */
.dl-card{border-radius:var(--r-xl);padding:1.5rem 1.6rem;background:linear-gradient(160deg,rgba(79,139,255,0.07),rgba(79,139,255,0.02));border:1px solid rgba(79,139,255,0.15);margin-bottom:1rem;margin-top:1.5rem;}
.dl-title{font-family:var(--font-head);font-size:1.2rem;font-weight:700;color:#fff;margin-bottom:0.3rem;}
.dl-sub{font-size:0.92rem;color:#8aaccc;line-height:1.65;}
.footer-note{text-align:center;font-size:0.8rem;color:#2a3847;padding:1.5rem 0 0.5rem;}
/* Success/info bars */
.success-bar{background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);border-radius:14px;padding:0.75rem 1rem;color:#86efac;font-size:0.9rem;margin:0.5rem 0;}
.info-bar{background:rgba(79,139,255,0.06);border:1px solid rgba(79,139,255,0.16);border-radius:14px;padding:0.75rem 1rem;color:#a8c4ff;font-size:0.88rem;margin:0.5rem 0;}
/* Score ring colors */
.score-high{color:#22c55e!important;}
.score-med{color:#f59e0b!important;}
.score-low{color:#ef4444!important;}
</style>
""", unsafe_allow_html=True)

# ─── IMPORTS (after auth) ─────────────────────────────────────────────────────
from resume_processor import ResumeProcessor
from gemini_client import GeminiClient, ATSUtils

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def reset_state_for_new_file():
    for k, v in [("ats_analysis", None), ("suggestions", []), ("choices_made", {}),
                 ("pdf_bytes", None), ("tailored_docx_bytes", None),
                 ("line_edits", {}), ("ready_for_manual_edit", False),
                 ("auto_applied", False)]:
        st.session_state[k] = v


def full_reset():
    for k in ["resume_processor", "ats_analysis", "suggestions", "choices_made",
              "pdf_bytes", "tailored_docx_bytes", "uploaded_filename",
              "uploaded_file_signature", "line_edits", "ready_for_manual_edit", "auto_applied"]:
        st.session_state[k] = None
    st.session_state["suggestions"] = []
    st.session_state["choices_made"] = {}
    st.session_state["line_edits"] = {}
    st.session_state["ready_for_manual_edit"] = False
    st.session_state["auto_applied"] = False


def extract_name(lines):
    for line in lines:
        text = line["text"].strip()
        words = text.split()
        if len(words) >= 2:
            return f"{words[0]}_{words[1]}"
    return "Candidate"


def extract_job_title(jd):
    for line in jd.strip().split("\n")[:5]:
        line = line.strip()
        if line and len(line) < 80 and not line.lower().startswith(("about", "we ", "company")):
            return re.sub(r"[^\w\s]", "", line).replace(" ", "_")[:40]
    return "Role"


def render_progress(label, pct):
    st.markdown(f"""
<div class="load-wrap">
  <div class="load-header">
    <span class="load-label">{label}</span>
    <span class="load-pct">{pct}%</span>
  </div>
  <div class="load-track"><div class="load-fill" style="width:{pct}%"></div></div>
</div>
""", unsafe_allow_html=True)


def convert_to_pdf(docx_bytes):
    with tempfile.TemporaryDirectory() as tmpdir:
        inp = os.path.join(tmpdir, "resume.docx")
        with open(inp, "wb") as f:
            f.write(docx_bytes)
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", inp, "--outdir", tmpdir],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice error: {result.stderr}")
        out = os.path.join(tmpdir, "resume.pdf")
        if not os.path.exists(out):
            raise RuntimeError("PDF not created.")
        with open(out, "rb") as f:
            return f.read()


SOFFICE_AVAILABLE = shutil.which("soffice") is not None

# ─── API CLIENT ───────────────────────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("GEMINI_API_KEY not found in Streamlit secrets.")
    st.stop()

client = GeminiClient(GEMINI_API_KEY)

# ─── SESSION DEFAULTS ─────────────────────────────────────────────────────────
_defaults = {
    "resume_processor": None, "ats_analysis": None, "suggestions": [],
    "choices_made": {}, "pdf_bytes": None, "tailored_docx_bytes": None,
    "uploaded_filename": None, "uploaded_file_signature": None,
    "line_edits": {}, "line_char_limit": 90,
    "ready_for_manual_edit": False, "auto_applied": False,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── TOPBAR ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
  <div class="brand">
    <div class="brand-dot">✦</div>
    <div>
      <div class="brand-name">Rizzume</div>
      <div class="brand-tagline">ATS-maximizing resume tailor — layout stays perfect</div>
    </div>
  </div>
  <div class="topbar-pills">
    <div class="tpill">ATS Match</div>
    <div class="tpill">Keyword Placement</div>
    <div class="tpill">5 Options / Line</div>
    <div class="tpill">Format Safe</div>
    <div class="tpill">DOCX + PDF</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── WORKFLOW INDICATOR ───────────────────────────────────────────────────────
_step = 0
if st.session_state.resume_processor: _step = 1
if st.session_state.ats_analysis: _step = 2
if st.session_state.suggestions: _step = 3
if st.session_state.ready_for_manual_edit: _step = 4
_labels = ["Upload Resume", "ATS Analysis", "AI Suggestions", "Edit & Export"]
render_progress(f"Step {_step}/4 — {_labels[min(_step,3)]}", int(_step / 4 * 100))

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="sec-card">
  <div class="step-tag">Step 01</div>
  <div class="sec-title">Upload Resume & Job Description</div>
  <div class="sec-sub">Upload your DOCX resume and paste the job description. Then run ATS analysis to see keyword gaps.</div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1.4], gap="large")

with col_left:
    uploaded_file = st.file_uploader("Upload your resume (.docx)", type=["docx"])

with col_right:
    job_description = st.text_area(
        "Paste Job Description",
        height=280,
        placeholder="Paste the full job description here…",
    )

# Handle new file upload
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    sig = (uploaded_file.name, len(file_bytes))
    if st.session_state.uploaded_file_signature != sig:
        st.session_state.resume_processor = ResumeProcessor(file_bytes)
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.uploaded_file_signature = sig
        reset_state_for_new_file()
        st.markdown('<div class="success-bar">✅ Resume uploaded — ready to analyze.</div>', unsafe_allow_html=True)

# Action buttons
btn1, btn2, _ = st.columns([1.2, 0.8, 4], gap="large")

with btn1:
    if st.button("🔍 Analyze ATS Match", use_container_width=True):
        if st.session_state.resume_processor is None:
            st.warning("Please upload a resume first.")
        elif not job_description.strip():
            st.warning("Please paste the job description.")
        else:
            resume_text = "\n".join(
                l["text"] for l in st.session_state.resume_processor.get_all_lines()
                if l["text"].strip()
            )
            render_progress("Running ATS analysis…", 25)
            with st.spinner(""):
                try:
                    ats = client.analyze_ats(resume_text, job_description)
                    st.session_state.ats_analysis = ats
                    st.session_state.suggestions = []
                    st.session_state.choices_made = {}
                    st.session_state.tailored_docx_bytes = None
                    st.session_state.pdf_bytes = None
                    st.session_state.ready_for_manual_edit = False
                    st.session_state.auto_applied = False
                    render_progress("ATS analysis complete", 50)
                    st.success(f"Analysis complete. ATS score: {ats.get('ats_score',0)}% · {len(ats.get('missing_keywords',[]))} keywords missing.")
                except Exception as e:
                    st.error(f"ATS analysis failed: {e}")

with btn2:
    if st.button("↺ Reset", use_container_width=True):
        full_reset()
        st.rerun()

# Resume line preview
if st.session_state.resume_processor:
    with st.expander("📄 Preview extracted resume lines"):
        for line in st.session_state.resume_processor.get_all_lines():
            if line["text"].strip():
                st.code(f'[{line["index"]}] {line["text"]}', language=None)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — ATS ANALYSIS RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.resume_processor and not st.session_state.ats_analysis:
    st.markdown('<div class="info-bar">📊 Click <strong>Analyze ATS Match</strong> above to see keyword gaps and generate rewrites.</div>', unsafe_allow_html=True)

if st.session_state.ats_analysis:
    ats = st.session_state.ats_analysis
    ats_score = int(ats.get("ats_score", 0))
    score_class = "score-high" if ats_score >= 75 else ("score-med" if ats_score >= 50 else "score-low")

    st.markdown("""
<div class="sec-card">
  <div class="step-tag">Step 02</div>
  <div class="sec-title">ATS Analysis Results</div>
  <div class="sec-sub">Review your keyword coverage before generating AI rewrites.</div>
</div>
""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4, gap="large")
    for col, label, val in [
        (c1, "ATS Score", f"{ats_score}%"),
        (c2, "Present Keywords", str(len(ats.get("present_keywords", [])))),
        (c3, "Missing Keywords", str(len(ats.get("missing_keywords", [])))),
        (c4, "Priority Targets", str(len(ats.get("recommended_keyword_targets", [])))),
    ]:
        with col:
            st.markdown('<div class="metric-shell">', unsafe_allow_html=True)
            st.metric(label, val)
            st.markdown('</div>', unsafe_allow_html=True)

    if ats.get("score_note"):
        st.info(ats["score_note"])

    kw_col1, kw_col2 = st.columns(2, gap="large")
    with kw_col1:
        present = ats.get("present_keywords", [])
        html = "".join(f'<span class="chip-ok">{k}</span>' for k in present) or '<span style="color:var(--muted)">None detected</span>'
        st.markdown(f'<div class="kw-box"><div class="kw-title">✓ Present in Resume ({len(present)})</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

    with kw_col2:
        targets = ats.get("recommended_keyword_targets", []) or ats.get("missing_keywords", [])
        html = "".join(f'<span class="chip-miss">{k}</span>' for k in targets) or '<span style="color:var(--muted)">None!</span>'
        st.markdown(f'<div class="kw-box"><div class="kw-title">⚠ Priority Keywords to Add ({len(targets)})</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

    if ats.get("key_requirements"):
        st.markdown("**Key Requirements from Job Description:**")
        for req in ats["key_requirements"][:8]:
            st.markdown(f'<div class="req-item">→ {req}</div>', unsafe_allow_html=True)

    # ── Generation controls ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("**Generation Settings**")
    p_col, s_col = st.columns([1, 2], gap="large")
    with p_col:
        preset = st.selectbox("Format Preset", ["Compact (80)", "Balanced (90)", "Relaxed (105)"], index=1)
    preset_map = {"Compact (80)": 80, "Balanced (90)": 90, "Relaxed (105)": 105}
    default_limit = preset_map[preset]
    with s_col:
        line_char_limit = st.slider(
            "Max characters per visual line",
            min_value=60, max_value=130,
            value=st.session_state.get("line_char_limit", default_limit),
            step=5,
            help="Controls rewrite length. Compact keeps lines tight, Relaxed allows slightly longer bullets.",
        )
    st.session_state.line_char_limit = line_char_limit

    gen_col, _ = st.columns([1.5, 4], gap="large")
    with gen_col:
        if st.button("✨ Generate AI Suggestions (All Keywords)", use_container_width=True):
            lines = st.session_state.resume_processor.get_all_lines(include_empty=False)
            render_progress("Generating AI rewrites — this takes ~20-40 seconds…", 60)
            with st.spinner("AI is analyzing every line and placing all keywords naturally…"):
                try:
                    target_keywords = ATSUtils.dedupe(
                        ats.get("recommended_keyword_targets", [])
                        + ats.get("high_priority_missing", [])
                        + ats.get("missing_keywords", [])
                    )
                    sugs = client.generate_suggestions(
                        lines=lines,
                        job_description=job_description,
                        ats_analysis=ats,
                        selected_keywords=target_keywords,
                        line_char_limit=st.session_state.line_char_limit,
                    )
                    st.session_state.suggestions = sugs
                    st.session_state.choices_made = {}
                    st.session_state.tailored_docx_bytes = None
                    st.session_state.pdf_bytes = None
                    st.session_state.ready_for_manual_edit = False
                    st.session_state.auto_applied = False
                    render_progress("Suggestions ready", 75)
                    # Count unique keywords covered
                    placed_kws = ATSUtils.dedupe(
                        [kw for s in sugs for kw in s.get("keywords_added", [])]
                    )
                    st.success(
                        f"✦ Generated {len(sugs)} line rewrites covering {len(placed_kws)} keywords. "
                        f"Review below and pick your preferred version for each line."
                    )
                except Exception as e:
                    st.error(f"Generation failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — SUGGESTIONS
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.ats_analysis and not st.session_state.suggestions:
    st.markdown('<div class="info-bar">Click <strong>Generate AI Suggestions</strong> above to get keyword-optimized rewrites for each resume line.</div>', unsafe_allow_html=True)

if st.session_state.suggestions:
    sugs = st.session_state.suggestions
    all_target_kws = ATSUtils.dedupe(
        (st.session_state.ats_analysis or {}).get("recommended_keyword_targets", [])
        + (st.session_state.ats_analysis or {}).get("missing_keywords", [])
    )

    # Keyword coverage summary
    chosen_count = len(st.session_state.choices_made)
    total_sugs = len(sugs)
    placed_kws = ATSUtils.dedupe([
        kw for i, s in enumerate(sugs)
        for kw in s.get("keywords_added", [])
        if i in st.session_state.choices_made
    ])
    
    st.markdown(f"""
<div class="sec-card">
  <div class="step-tag">Step 03</div>
  <div class="sec-title">AI-Generated Rewrites</div>
  <div class="sec-sub">
    {total_sugs} lines rewritten to maximize keyword coverage.
    Select your preferred version for each line, then click <strong>Apply &amp; Open Editor</strong>.
    Use <strong>Select All Best Options</strong> to auto-pick the most keyword-rich version.
  </div>
</div>
""", unsafe_allow_html=True)

    render_progress(
        f"Selections: {chosen_count}/{total_sugs} · Keywords covered: {len(placed_kws)}",
        int(chosen_count / total_sugs * 100) if total_sugs else 0
    )

    # ── Quick-action buttons ──────────────────────────────────────────────────
    qa1, qa2, qa3 = st.columns([1.4, 1.4, 3], gap="large")
    with qa1:
        if st.button("⚡ Select All Best Options", use_container_width=True):
            # Auto-select the last option (most keyword-dense) for every suggestion
            for i, sug in enumerate(sugs):
                if sug.get("options"):
                    st.session_state.choices_made[i] = sug["options"][-1]
            st.rerun()
    with qa2:
        if st.button("↩ Clear All Selections", use_container_width=True):
            st.session_state.choices_made = {}
            st.rerun()

    # Show keyword coverage across suggestions
    all_placed = ATSUtils.dedupe([kw for s in sugs for kw in s.get("keywords_added", [])])
    still_missing = [kw for kw in all_target_kws if not ATSUtils.keyword_in_text(" ".join(all_placed), kw)]
    
    cov_col1, cov_col2 = st.columns(2, gap="large")
    with cov_col1:
        html = "".join(f'<span class="chip-placed">{k}</span>' for k in all_placed[:30]) or "None yet"
        st.markdown(f'<div class="kw-box"><div class="kw-title">✦ Keywords Covered in Suggestions ({len(all_placed)})</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)
    with cov_col2:
        html = "".join(f'<span class="chip-miss">{k}</span>' for k in still_missing[:20]) or '<span style="color:#22c55e">All covered!</span>'
        st.markdown(f'<div class="kw-box"><div class="kw-title">⚠ Still Missing ({len(still_missing)})</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Per-line suggestion cards ─────────────────────────────────────────────
    for i, sug in enumerate(sugs):
        li = sug.get("line_index", "?")
        original = sug.get("original", "")
        options = sug.get("options", [])
        reason = sug.get("reason", "")
        keywords_added = sug.get("keywords_added", [])
        char_budget = sug.get("char_budget")

        st.markdown('<div class="sug-card">', unsafe_allow_html=True)

        # Header with keywords
        kw_badges = "".join(f'<span class="kw-badge">+{k}</span>' for k in keywords_added[:6])
        st.markdown(f'<div class="line-label">Line {li}&nbsp;&nbsp;{kw_badges}</div>', unsafe_allow_html=True)

        # Original line
        st.code(original, language=None)

        if reason:
            st.markdown(f'<div class="reason-box">🔎 {reason}</div>', unsafe_allow_html=True)

        if char_budget:
            st.caption(f"Character budget: up to {char_budget} chars")

        # Radio options
        radio_opts = ["— Keep original —"] + options
        cur = st.session_state.choices_made.get(i, "— Keep original —")
        if cur not in radio_opts:
            cur = "— Keep original —"

        sel = st.radio(
            f"line_{li}",
            radio_opts,
            index=radio_opts.index(cur),
            key=f"r_{i}",
            label_visibility="collapsed",
        )

        if sel == "— Keep original —":
            st.session_state.choices_made.pop(i, None)
        else:
            st.session_state.choices_made[i] = sel

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Apply button ──────────────────────────────────────────────────────────
    st.markdown("---")
    ap1, _ = st.columns([1.5, 4], gap="large")
    with ap1:
        if st.button("✅ Apply Selected Changes & Open Editor", use_container_width=True):
            if st.session_state.resume_processor is None:
                st.error("Resume processor missing. Re-upload your resume.")
            else:
                try:
                    src_bytes = uploaded_file.getvalue() if uploaded_file else st.session_state.resume_processor.export()
                    fresh = ResumeProcessor(src_bytes)

                    applied = 0
                    for i, sug in enumerate(sugs):
                        chosen = st.session_state.choices_made.get(i)
                        if chosen:
                            fresh.replace_line(sug["line_index"], chosen)
                            applied += 1

                    st.session_state.resume_processor = fresh
                    st.session_state.tailored_docx_bytes = fresh.export()
                    st.session_state.pdf_bytes = None
                    st.session_state.line_edits = {}
                    for line in fresh.get_all_lines():
                        if line["text"].strip():
                            st.session_state.line_edits[line["index"]] = line["text"]

                    st.session_state.ready_for_manual_edit = True
                    render_progress(f"Applied {applied} rewrites — editor ready", 90)
                    st.success(f"✦ {applied} line(s) updated. Fine-tune in the editor below, then export.")
                except Exception as e:
                    st.error(f"Failed to apply: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — MANUAL EDITOR + EXPORT
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.resume_processor is not None and st.session_state.ready_for_manual_edit:
    ats = st.session_state.ats_analysis or {}
    lines = st.session_state.resume_processor.get_all_lines()
    name_part = extract_name(lines)
    job_part = extract_job_title(job_description or "")
    file_stem = f"{name_part}_{job_part}_Tailored"

    st.markdown("""
<div class="sec-card">
  <div class="step-tag">Step 04</div>
  <div class="sec-title">Fine-Tune & Export</div>
  <div class="sec-sub">
    All selected rewrites are applied. Edit any line manually, reference keyword lists on the right,
    then click <strong>Save Edits → Rebuild DOCX</strong> before exporting.
  </div>
</div>
""", unsafe_allow_html=True)

    edit_col, kw_col = st.columns([2.2, 1], gap="large")

    with edit_col:
        st.markdown('<div class="info-bar">✏️ Edit lines below. Click <strong>Save Edits → Rebuild DOCX</strong> when done.</div>', unsafe_allow_html=True)

        editable_lines = [l for l in lines if l["text"].strip()]

        st.markdown('<div class="editor-wrap"><div class="editor-header"><span style="font-size:0.75rem;font-weight:700;color:#7a90b0;text-transform:uppercase;letter-spacing:0.09em;">Line Editor</span></div>', unsafe_allow_html=True)

        for l in editable_lines:
            idx = l["index"]
            c_idx, c_edit = st.columns([0.08, 0.92], gap="small")
            with c_idx:
                st.markdown(f'<div style="padding:0.55rem 0;text-align:center;font-size:0.72rem;font-weight:700;color:#4a5a72;font-family:var(--font-mono);">{idx}</div>', unsafe_allow_html=True)
            with c_edit:
                new_val = st.text_input(
                    label=f"line_{idx}",
                    value=st.session_state.line_edits.get(idx, l["text"]),
                    key=f"le_{idx}",
                    label_visibility="collapsed",
                )
                st.session_state.line_edits[idx] = new_val

        st.markdown('</div>', unsafe_allow_html=True)

        save_col, _ = st.columns([1, 3])
        with save_col:
            if st.button("💾 Save Edits → Rebuild DOCX", use_container_width=True):
                try:
                    src_bytes = uploaded_file.getvalue() if uploaded_file else st.session_state.resume_processor._original_bytes
                    fresh = ResumeProcessor(src_bytes)

                    # Re-apply chosen suggestions
                    for i, sug in enumerate(st.session_state.suggestions):
                        chosen = st.session_state.choices_made.get(i)
                        if chosen:
                            fresh.replace_line(sug["line_index"], chosen)

                    # Apply manual edits on top
                    current_lines = st.session_state.resume_processor.get_all_lines()
                    orig_map = {l["index"]: l["text"] for l in current_lines}
                    for idx, new_text in st.session_state.line_edits.items():
                        if orig_map.get(idx) != new_text:
                            fresh.replace_line(idx, new_text)

                    st.session_state.resume_processor = fresh
                    st.session_state.tailored_docx_bytes = fresh.export()
                    st.session_state.pdf_bytes = None

                    for line in fresh.get_all_lines():
                        if line["text"].strip():
                            st.session_state.line_edits[line["index"]] = line["text"]

                    render_progress("DOCX rebuilt with all edits", 97)
                    st.success("✦ DOCX rebuilt. Download below.")
                except Exception as e:
                    st.error(f"Failed to rebuild: {e}")

    with kw_col:
        st.markdown("""
<div class="sec-card" style="padding:1.1rem;">
  <div class="sec-title" style="font-size:1rem;">Keyword Reference</div>
  <div class="sec-sub" style="font-size:0.83rem;">Use these while editing lines manually.</div>
</div>
""", unsafe_allow_html=True)

        present = ats.get("present_keywords", [])
        targets = ats.get("recommended_keyword_targets", []) or ats.get("missing_keywords", [])
        missing = ats.get("missing_keywords", [])

        html = "".join(f'<span class="chip-miss">{k}</span>' for k in targets[:25]) or "None"
        st.markdown(f'<div class="kw-box"><div class="kw-title">🎯 Priority Targets</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

        html = "".join(f'<span class="chip-miss">{k}</span>' for k in missing[:30]) or "None"
        st.markdown(f'<div class="kw-box"><div class="kw-title">⚠ All Missing</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

        html = "".join(f'<span class="chip-ok">{k}</span>' for k in present[:20]) or "None"
        st.markdown(f'<div class="kw-box"><div class="kw-title">✓ Already Present</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

    # ── Export section ────────────────────────────────────────────────────────
    current_docx = (
        st.session_state.tailored_docx_bytes
        if st.session_state.tailored_docx_bytes is not None
        else st.session_state.resume_processor.export()
    )

    st.markdown(f"""
<div class="dl-card">
  <div class="dl-title">Export Your Tailored Resume</div>
  <div class="dl-sub">Download the fully tailored DOCX. Your layout, fonts, and formatting are preserved.</div>
</div>
""", unsafe_allow_html=True)

    d1, d2, d3 = st.columns(3, gap="large")

    with d1:
        st.markdown('<div style="font-size:0.8rem;font-weight:700;color:#8a9eb8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;">Word Document</div>', unsafe_allow_html=True)
        st.download_button(
            label="⬇ Download DOCX",
            data=current_docx,
            file_name=f"{file_stem}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        st.markdown('<div style="font-size:0.78rem;color:#5a6880;margin-top:0.4rem;">All rewrites + manual edits included.</div>', unsafe_allow_html=True)

    with d2:
        st.markdown('<div style="font-size:0.8rem;font-weight:700;color:#8a9eb8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;">PDF Export</div>', unsafe_allow_html=True)
        if SOFFICE_AVAILABLE:
            if st.button("⚙ Generate PDF", use_container_width=True):
                with st.spinner("Converting…"):
                    try:
                        st.session_state.pdf_bytes = convert_to_pdf(current_docx)
                        st.success("PDF ready.")
                    except Exception as e:
                        st.error(f"PDF failed: {e}")
            if st.session_state.pdf_bytes:
                st.download_button(
                    label="⬇ Download PDF",
                    data=st.session_state.pdf_bytes,
                    file_name=f"{file_stem}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.markdown('<div style="font-size:0.84rem;color:#5a6880;padding:0.6rem 0;">PDF unavailable — LibreOffice not installed.</div>', unsafe_allow_html=True)

    with d3:
        st.markdown('<div style="font-size:0.8rem;font-weight:700;color:#8a9eb8;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;">Google Docs</div>', unsafe_allow_html=True)
        st.markdown("""
<div style="background:rgba(79,139,255,0.07);border:1px solid rgba(79,139,255,0.18);border-radius:16px;padding:1rem;">
  <ol style="font-size:0.83rem;color:#9ab0cc;line-height:1.8;margin:0 0 0.85rem 1.1rem;padding:0;">
    <li>Download the <strong style="color:#c5daff">DOCX</strong></li>
    <li>Go to Google Drive</li>
    <li>Upload &amp; open with Google Docs</li>
  </ol>
  <a href="https://drive.google.com/drive/my-drive" target="_blank"
     style="display:flex;align-items:center;justify-content:center;gap:0.5rem;padding:0.7rem 1rem;border-radius:12px;background:linear-gradient(135deg,#3a74f0,#5d95ff);color:#fff;font-size:0.88rem;font-weight:700;text-decoration:none;box-shadow:0 6px 18px rgba(79,139,255,0.32);">
    Open Google Drive ↗
  </a>
</div>
""", unsafe_allow_html=True)

    render_progress("Resume tailored and ready to export ✦", 100)

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown('<div class="footer-note">Rizzume ✦ — ATS-maximizing resume tailor · Layout always preserved</div>', unsafe_allow_html=True)
