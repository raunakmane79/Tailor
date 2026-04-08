import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List

import streamlit as st

from gemini_client import ATSUtils, GeminiClient
from resume_processor import ResumeProcessor


st.set_page_config(page_title="Rizzume Pro", page_icon="✦", layout="wide")

st.markdown(
    """
<style>
:root {
  --bg:#07101d; --card:#0f1b2d; --card2:#13233b; --text:#ecf2ff; --muted:#a8b7cc;
  --border:rgba(255,255,255,.10); --accent:#5b8cff; --accent2:#87abff; --ok:#22c55e; --warn:#f59e0b;
}
html, body, [class*="css"] { background: var(--bg) !important; color: var(--text) !important; }
.stApp {
  background:
  radial-gradient(circle at top left, rgba(91,140,255,.16), transparent 35%),
  radial-gradient(circle at bottom right, rgba(91,140,255,.10), transparent 30%),
  var(--bg);
}
.block-container { padding-top: 1.1rem; padding-bottom: 2rem; }
.card {
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  border:1px solid var(--border); border-radius:22px; padding:1.2rem 1.25rem; margin-bottom: 1rem;
  box-shadow: 0 18px 44px rgba(0,0,0,.22);
}
.hero { padding:1.5rem 1.4rem; border-radius:26px; }
.small { color:var(--muted); font-size:.92rem; line-height:1.6; }
.badge { display:inline-block; padding:.28rem .6rem; border-radius:999px; border:1px solid var(--border); margin:.18rem .2rem 0 0; font-size:.8rem; }
.ok { background: rgba(34,197,94,.12); border-color: rgba(34,197,94,.22); }
.miss { background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.22); }
.plan { background: rgba(255,255,255,.03); border:1px solid var(--border); border-radius:16px; padding:1rem; margin-bottom:.8rem; }
.kicker { color:#cfe0ff; font-size:.76rem; text-transform:uppercase; letter-spacing:.12em; font-weight:700; }
.title { font-size:2rem; font-weight:800; margin:.2rem 0 .45rem; letter-spacing:-.04em; }
.mini { font-size:.8rem; color:var(--muted); }
hr { border:none; border-top:1px solid rgba(255,255,255,.08); margin:.9rem 0; }
section[data-testid="stSidebar"] { border-right:1px solid rgba(255,255,255,.08); }
</style>
""",
    unsafe_allow_html=True,
)


def check_password() -> bool:
    if "_auth" not in st.session_state:
        st.session_state["_auth"] = False
    secret = st.secrets.get("APP_PASSWORD", "")
    if not secret:
        return True
    if st.session_state["_auth"]:
        return True

    st.markdown('<div class="card hero"><div class="kicker">Private workspace</div><div class="title">Rizzume Pro</div><div class="small">Professional keyword coverage, layout-safe rewrites, and manual control.</div></div>', unsafe_allow_html=True)
    with st.form("login"):
        login_id = st.text_input("Login ID")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")
        if submitted:
            if password == secret:
                st.session_state["_auth"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()


def init_state() -> None:
    defaults = {
        "resume_processor": None,
        "uploaded_signature": None,
        "ats_analysis": None,
        "rewrite_plan": [],
        "tailored_docx_bytes": None,
        "manual_edits": {},
        "job_description": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()

SOFFICE_AVAILABLE = shutil.which("soffice") is not None
client = GeminiClient(st.secrets["GEMINI_API_KEY"])


def reset_for_new_file() -> None:
    st.session_state["ats_analysis"] = None
    st.session_state["rewrite_plan"] = []
    st.session_state["tailored_docx_bytes"] = None
    st.session_state["manual_edits"] = {}



def convert_docx_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "resume.docx")
        with open(input_path, "wb") as f:
            f.write(docx_bytes)
        proc = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", input_path, "--outdir", tmpdir],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout or "LibreOffice conversion failed.")
        pdf_path = os.path.join(tmpdir, "resume.pdf")
        with open(pdf_path, "rb") as f:
            return f.read()



def get_resume_text(processor: ResumeProcessor) -> str:
    return "\n".join(line["text"] for line in processor.get_all_lines(include_empty=False) if line["text"])



def apply_plan_and_manual_edits(processor: ResumeProcessor, plan: List[Dict], manual_edits: Dict[int, str]) -> bytes:
    payload = []
    for item in plan:
        if item.get("apply", True):
            payload.append({"line_index": item["line_index"], "selected_text": item["selected_text"]})
    processor.apply_rewrites(payload)
    for raw_idx, new_text in manual_edits.items():
        try:
            line_index = int(raw_idx)
        except Exception:
            continue
        if isinstance(new_text, str) and new_text.strip():
            processor.replace_line(line_index, new_text)
    return processor.export()


st.markdown(
    '<div class="card hero"><div class="kicker">Resume Tailor</div><div class="title">Maximum truthful keyword match without breaking layout</div><div class="small">This version is built around keyword coverage planning first, then layout-safe rewrites. It aims for the highest truthful match possible and shows exactly which keywords each rewrite adds.</div></div>',
    unsafe_allow_html=True,
)

left, right = st.columns([1.1, 0.9], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload resume (.docx)", type=["docx"])
    job_description = st.text_area(
        "Paste job description",
        value=st.session_state.get("job_description", ""),
        height=320,
        placeholder="Paste the full JD here...",
    )
    st.session_state["job_description"] = job_description

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        signature = (uploaded_file.name, len(file_bytes), hash(file_bytes[:2000]))
        if st.session_state["uploaded_signature"] != signature:
            st.session_state["resume_processor"] = ResumeProcessor(file_bytes)
            st.session_state["uploaded_signature"] = signature
            reset_for_new_file()

    a1, a2 = st.columns(2)
    analyze = a1.button("Analyze ATS", use_container_width=True, type="primary")
    plan = a2.button("Build Rewrite Plan", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    processor = st.session_state.get("resume_processor")
    if analyze:
        if processor is None:
            st.error("Upload a DOCX resume first.")
        elif not job_description.strip():
            st.error("Paste the job description first.")
        else:
            with st.spinner("Analyzing ATS coverage..."):
                resume_text = get_resume_text(processor)
                st.session_state["ats_analysis"] = client.analyze_ats(resume_text, job_description)
                st.session_state["rewrite_plan"] = []
                st.session_state["tailored_docx_bytes"] = None

    if plan:
        if processor is None:
            st.error("Upload a DOCX resume first.")
        elif not job_description.strip():
            st.error("Paste the job description first.")
        else:
            if not st.session_state.get("ats_analysis"):
                resume_text = get_resume_text(processor)
                st.session_state["ats_analysis"] = client.analyze_ats(resume_text, job_description)
            with st.spinner("Building high-coverage rewrite plan..."):
                lines = processor.get_all_lines(include_empty=False)
                rewrite_plan = client.build_keyword_coverage_plan(
                    lines=lines,
                    job_description=job_description,
                    ats_analysis=st.session_state["ats_analysis"],
                    line_char_limit=95,
                    max_rewrites=16,
                    options_per_line=2,
                )
                for item in rewrite_plan:
                    item["apply"] = True
                st.session_state["rewrite_plan"] = rewrite_plan
                st.session_state["tailored_docx_bytes"] = None

with right:
    ats = st.session_state.get("ats_analysis")
    st.markdown('<div class="card"><div class="kicker">ATS Snapshot</div>', unsafe_allow_html=True)
    if ats:
        c1, c2 = st.columns(2)
        c1.metric("ATS score", f"{ats['ats_score']}%")
        c2.metric("Missing keywords", len(ats.get("missing_keywords", [])))
        st.caption(ats.get("score_note", ""))

        st.markdown("**High-priority missing keywords**")
        for kw in ats.get("high_priority_missing", [])[:18]:
            st.markdown(f'<span class="badge miss">{kw}</span>', unsafe_allow_html=True)

        st.markdown("<br>**Already present keywords**", unsafe_allow_html=True)
        for kw in ats.get("present_keywords", [])[:18]:
            st.markdown(f'<span class="badge ok">{kw}</span>', unsafe_allow_html=True)

        if ats.get("key_requirements"):
            st.markdown("<br>**Key requirements**", unsafe_allow_html=True)
            for req in ats["key_requirements"][:8]:
                st.write(f"- {req}")
    else:
        st.markdown('<div class="small">Upload a DOCX and run analysis to see keyword coverage and rewrite targets.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

rewrite_plan = st.session_state.get("rewrite_plan", [])
processor = st.session_state.get("resume_processor")
ats = st.session_state.get("ats_analysis")

if rewrite_plan:
    st.markdown('<div class="card"><div class="kicker">Rewrite Plan</div><div class="small">Each rewrite is mapped to real missing keywords. You can keep the best option, switch to option 2, or turn a rewrite off.</div></div>', unsafe_allow_html=True)
    covered = ATSUtils.dedupe_keep_order([kw for item in rewrite_plan for kw in item.get("keywords_added", [])])
    st.info(f"Planned keyword coverage: {len(covered)} keywords across {len(rewrite_plan)} lines.")

    for idx, item in enumerate(rewrite_plan):
        st.markdown('<div class="plan">', unsafe_allow_html=True)
        c1, c2 = st.columns([0.08, 0.92])
        item["apply"] = c1.checkbox("", value=item.get("apply", True), key=f"apply_{idx}")
        with c2:
            st.markdown(f"**Line {item['line_index']}**")
            st.caption(f"Targeted keywords: {', '.join(item.get('keywords_targeted', [])[:8]) or 'None'}")
            st.code(item["original"], language=None)
            option_labels = []
            for opt_idx, option in enumerate(item.get("options", []), start=1):
                label = f"Option {opt_idx}: {option}"
                option_labels.append(label)
            choice = st.radio(
                f"Choose rewrite for line {item['line_index']}",
                options=option_labels,
                index=0,
                key=f"choice_{idx}",
                label_visibility="collapsed",
            )
            chosen_option = item["options"][option_labels.index(choice)]
            item["selected_text"] = chosen_option
            live_hits = ATSUtils.find_keyword_hits(chosen_option, ats.get("missing_keywords", []) if ats else [])
            st.caption(f"Keywords added now: {', '.join(live_hits) or 'No tracked keywords detected'}")
            if item.get("reason"):
                st.write(item["reason"])
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="kicker">Manual Final Pass</div><div class="small">Edit any line directly before exporting. This is useful for tightening tone or fitting one last keyword naturally.</div>', unsafe_allow_html=True)
    editable_rewrite_lines = [item for item in rewrite_plan if item.get("apply", True)]
    for item in editable_rewrite_lines:
        current_text = item.get("selected_text") or item["original"]
        new_text = st.text_input(
            f"Manual edit for line {item['line_index']}",
            value=current_text,
            key=f"manual_{item['line_index']}",
        )
        st.session_state["manual_edits"][item["line_index"]] = new_text
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Build Final Resume", type="primary", use_container_width=True):
        with st.spinner("Applying rewrites and rebuilding DOCX..."):
            source_bytes = uploaded_file.getvalue() if uploaded_file is not None else processor.export()
            fresh_processor = ResumeProcessor(source_bytes)
            final_docx = apply_plan_and_manual_edits(fresh_processor, rewrite_plan, st.session_state.get("manual_edits", {}))
            st.session_state["tailored_docx_bytes"] = final_docx

final_docx = st.session_state.get("tailored_docx_bytes")
if final_docx:
    st.markdown('<div class="card"><div class="kicker">Export</div><div class="small">Your DOCX now includes selected rewrites and manual edits.</div>', unsafe_allow_html=True)
    st.download_button(
        "Download tailored DOCX",
        data=final_docx,
        file_name="tailored_resume.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
    if SOFFICE_AVAILABLE:
        try:
            pdf_bytes = convert_docx_to_pdf_bytes(final_docx)
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name="tailored_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.warning(f"PDF conversion failed: {exc}")
    st.markdown('</div>', unsafe_allow_html=True)
