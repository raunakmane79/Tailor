import streamlit as st
import json
import io
from resume_processor import ResumeProcessor
from gemini_client import GeminiClient

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Resume Tailor AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --ink: #0f0e0c;
    --paper: #f5f2ed;
    --accent: #c8472a;
    --accent2: #2a6fc8;
    --muted: #7a7570;
    --border: #d4cfc8;
    --card: #faf8f4;
}

html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
    background-color: var(--paper);
    color: var(--ink);
}

h1, h2, h3 { font-family: 'DM Serif Display', serif; }

.stApp { background-color: var(--paper); }

/* Header */
.app-header {
    display: flex; align-items: baseline; gap: 16px;
    border-bottom: 2px solid var(--ink);
    padding-bottom: 12px; margin-bottom: 32px;
}
.app-title { font-family: 'DM Serif Display', serif; font-size: 2.6rem; margin: 0; letter-spacing: -1px; }
.app-sub { font-size: 0.75rem; color: var(--muted); letter-spacing: 0.12em; text-transform: uppercase; }

/* Step indicator */
.step-row { display: flex; gap: 0; margin-bottom: 32px; }
.step-item {
    flex: 1; padding: 10px 16px; font-size: 0.7rem; letter-spacing: 0.1em;
    text-transform: uppercase; border: 1px solid var(--border);
    border-right: none; color: var(--muted); background: var(--card);
}
.step-item:last-child { border-right: 1px solid var(--border); }
.step-item.active { background: var(--ink); color: #fff; border-color: var(--ink); }
.step-item.done { background: var(--accent2); color: #fff; border-color: var(--accent2); }

/* Cards */
.info-card {
    background: var(--card); border: 1px solid var(--border);
    padding: 20px 24px; margin-bottom: 16px;
    border-left: 3px solid var(--accent);
}
.keyword-chip {
    display: inline-block; background: var(--ink); color: #fff;
    padding: 3px 10px; font-size: 0.7rem; letter-spacing: 0.08em;
    text-transform: uppercase; margin: 3px 3px 3px 0;
}
.keyword-chip.missing { background: var(--accent); }
.keyword-chip.present { background: var(--accent2); }

/* Choice buttons */
.choice-btn {
    display: block; width: 100%; text-align: left;
    background: var(--card); border: 1px solid var(--border);
    padding: 12px 16px; margin-bottom: 8px; cursor: pointer;
    font-family: 'DM Mono', monospace; font-size: 0.82rem;
    transition: all 0.15s;
}
.choice-btn:hover { border-color: var(--accent); background: #fff; }
.choice-btn.selected { border-color: var(--accent); border-width: 2px; background: #fff; }

/* Line preview */
.line-before { color: var(--muted); text-decoration: line-through; font-size: 0.8rem; padding: 6px 12px; background: #f0ede8; border: 1px solid var(--border); }
.line-after  { color: var(--ink); font-size: 0.82rem; padding: 6px 12px; background: #fff; border: 1px solid var(--accent2); border-left: 3px solid var(--accent2); }

/* Progress bar */
.ats-bar-wrap { background: var(--border); height: 8px; width: 100%; margin: 8px 0 4px; }
.ats-bar { height: 8px; background: var(--accent2); transition: width 0.5s; }

/* Metric boxes */
.metric-box { border: 1px solid var(--border); padding: 16px; text-align: center; background: var(--card); }
.metric-num { font-family: 'DM Serif Display', serif; font-size: 2rem; }
.metric-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }

/* Buttons */
.stButton > button {
    font-family: 'DM Mono', monospace !important;
    letter-spacing: 0.08em; text-transform: uppercase;
    font-size: 0.75rem !important;
    border-radius: 0 !important;
}
.stButton > button[kind="primary"] {
    background: var(--ink) !important; color: #fff !important;
    border: 2px solid var(--ink) !important;
}

hr.section-divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="app-title">Resume Tailor</div>
    <div class="app-sub">✦ ATS-Optimized · Format-Safe · Gemini-Powered</div>
</div>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
for key, default in {
    "step": 1,
    "resume_processor": None,
    "job_description": "",
    "ats_analysis": None,
    "suggestions": [],
    "suggestion_index": 0,
    "choices_made": {},
    "final_docx_bytes": None,
    "gemini_client": None,
    "api_key_set": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Step indicator ────────────────────────────────────────────────────────────
def render_steps():
    steps = ["1 · Upload", "2 · Job Description", "3 · ATS Analysis", "4 · Tailor Lines", "5 · Download"]
    html = '<div class="step-row">'
    for i, s in enumerate(steps, 1):
        cls = "active" if i == st.session_state.step else ("done" if i < st.session_state.step else "")
        html += f'<div class="step-item {cls}">{s}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

render_steps()

# ── STEP 0: API Key ───────────────────────────────────────────────────────────
with st.expander("⚙ Gemini API Key", expanded=not st.session_state.api_key_set):
    api_key = st.text_input("Enter your Gemini API Key", type="password", key="api_key_input",
                             placeholder="AIza...")
    if st.button("Set API Key"):
        if api_key.strip():
            st.session_state.gemini_client = GeminiClient(api_key.strip())
            st.session_state.api_key_set = True
            st.success("✓ API key saved for this session.")
        else:
            st.error("Please enter a valid API key.")

if not st.session_state.api_key_set:
    st.info("Set your Gemini API key above to get started. Get one free at [aistudio.google.com](https://aistudio.google.com/).")
    st.stop()

# ── STEP 1: Upload Resume ─────────────────────────────────────────────────────
if st.session_state.step == 1:
    st.markdown("### Upload Your Resume")
    st.markdown('<div class="info-card">Upload your <strong>.docx</strong> resume. The app will parse every line and track character counts so formatting is preserved exactly.</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader("Drop your resume here", type=["docx"], label_visibility="collapsed")

    if uploaded:
        with st.spinner("Parsing resume…"):
            rp = ResumeProcessor(uploaded.read())
            st.session_state.resume_processor = rp

        lines = rp.get_all_lines()
        st.markdown(f"**✓ Parsed {len(lines)} lines** across {len(rp.doc.paragraphs)} paragraphs + table cells.")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-box"><div class="metric-num">{len(lines)}</div><div class="metric-label">Total Lines</div></div>', unsafe_allow_html=True)
        with col2:
            avg_len = int(sum(l["char_count"] for l in lines) / max(len(lines), 1))
            st.markdown(f'<div class="metric-box"><div class="metric-num">{avg_len}</div><div class="metric-label">Avg Chars/Line</div></div>', unsafe_allow_html=True)
        with col3:
            max_len = max((l["char_count"] for l in lines), default=0)
            st.markdown(f'<div class="metric-box"><div class="metric-num">{max_len}</div><div class="metric-label">Max Chars/Line</div></div>', unsafe_allow_html=True)

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.markdown("**Line Preview (first 20):**")
        for line in lines[:20]:
            chars = line["char_count"]
            bar_color = "#2a6fc8" if chars < 100 else "#c8472a"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;font-size:0.75rem;">
                <span style="color:var(--muted);width:28px;text-align:right;">{line['index']}</span>
                <span style="flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{line['text'] or '<em style="color:var(--muted);">[empty]</em>'}</span>
                <span style="color:{bar_color};width:60px;text-align:right;">{chars} ch</span>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Continue →", type="primary"):
            st.session_state.step = 2
            st.rerun()

# ── STEP 2: Job Description ───────────────────────────────────────────────────
elif st.session_state.step == 2:
    st.markdown("### Paste the Job Description")
    st.markdown('<div class="info-card">Paste the full job description. Gemini will extract required skills, keywords, and responsibilities to tailor your resume.</div>', unsafe_allow_html=True)

    jd = st.text_area("Job Description", height=320, value=st.session_state.job_description,
                       placeholder="Paste job description here…", label_visibility="collapsed")
    st.session_state.job_description = jd

    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("← Back"):
            st.session_state.step = 1
            st.rerun()
    with col_b:
        if st.button("Analyze ATS →", type="primary"):
            if len(jd.strip()) < 50:
                st.error("Please paste a job description (at least 50 characters).")
            else:
                with st.spinner("Gemini is analyzing keywords and ATS match…"):
                    rp = st.session_state.resume_processor
                    resume_text = "\n".join(l["text"] for l in rp.get_all_lines() if l["text"].strip())
                    analysis = st.session_state.gemini_client.analyze_ats(resume_text, jd)
                    st.session_state.ats_analysis = analysis
                st.session_state.step = 3
                st.rerun()

# ── STEP 3: ATS Analysis ──────────────────────────────────────────────────────
elif st.session_state.step == 3:
    analysis = st.session_state.ats_analysis
    st.markdown("### ATS Keyword Analysis")

    score = analysis.get("ats_score", 0)
    bar_w = min(score, 100)
    score_color = "#c8472a" if score < 60 else ("#f0a500" if score < 80 else "#2a6fc8")

    st.markdown(f"""
    <div style="border:1px solid var(--border);padding:20px 24px;background:var(--card);margin-bottom:20px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;">
            <span style="font-family:'DM Serif Display',serif;font-size:1.1rem;">Current ATS Match Score</span>
            <span style="font-family:'DM Serif Display',serif;font-size:2.2rem;color:{score_color};">{score}%</span>
        </div>
        <div class="ats-bar-wrap"><div class="ats-bar" style="width:{bar_w}%;background:{score_color};"></div></div>
        <div style="font-size:0.7rem;color:var(--muted);">{analysis.get('score_note','')}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✓ Keywords Already Present**")
        present = analysis.get("present_keywords", [])
        chips = "".join(f'<span class="keyword-chip present">{k}</span>' for k in present) or "<em>None detected</em>"
        st.markdown(chips, unsafe_allow_html=True)

    with col2:
        st.markdown("**✗ Missing Keywords (must add)**")
        missing = analysis.get("missing_keywords", [])
        chips = "".join(f'<span class="keyword-chip missing">{k}</span>' for k in missing) or "<em>None — great match!</em>"
        st.markdown(chips, unsafe_allow_html=True)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    st.markdown("**Key Job Requirements Identified:**")
    for req in analysis.get("key_requirements", []):
        st.markdown(f"- {req}")

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1, 5])
    with col_a:
        if st.button("← Back"):
            st.session_state.step = 2
            st.rerun()
    with col_b:
        if st.button("Generate Tailoring Suggestions →", type="primary"):
            with st.spinner("Gemini is generating line-by-line suggestions…"):
                rp = st.session_state.resume_processor
                lines = [l for l in rp.get_all_lines() if l["text"].strip()]
                suggestions = st.session_state.gemini_client.generate_suggestions(
                    lines, st.session_state.job_description, st.session_state.ats_analysis
                )
                st.session_state.suggestions = suggestions
                st.session_state.suggestion_index = 0
                st.session_state.choices_made = {}
            st.session_state.step = 4
            st.rerun()

# ── STEP 4: Interactive Tailoring ─────────────────────────────────────────────
elif st.session_state.step == 4:
    suggestions = st.session_state.suggestions
    total = len(suggestions)

    if total == 0:
        st.info("No suggestions were generated. Your resume may already be well-optimized!")
        if st.button("Go to Download →", type="primary"):
            st.session_state.step = 5
            st.rerun()
    else:
        done_count = len(st.session_state.choices_made)
        st.markdown(f"### Tailor Each Line  <span style='font-size:0.85rem;color:var(--muted);font-family:DM Mono,monospace;'>({done_count}/{total} done)</span>", unsafe_allow_html=True)

        # Progress
        prog = done_count / total
        st.progress(prog)

        idx = st.session_state.suggestion_index
        if idx >= total:
            st.success(f"✓ All {total} suggestions reviewed!")
            if st.button("Preview & Download →", type="primary"):
                with st.spinner("Applying changes and building document…"):
                    rp = st.session_state.resume_processor
                    for s in suggestions:
                        chosen_idx = st.session_state.choices_made.get(s["line_index"], None)
                        if chosen_idx is not None and chosen_idx < len(s["options"]):
                            chosen_text = s["options"][chosen_idx]
                            rp.replace_line(s["line_index"], chosen_text)
                    st.session_state.final_docx_bytes = rp.save_to_bytes()
                st.session_state.step = 5
                st.rerun()
        else:
            sug = suggestions[idx]
            original = sug["original"]
            options = sug["options"]
            reason = sug.get("reason", "")
            keywords_added = sug.get("keywords_added", [])

            # Navigation breadcrumb
            st.markdown(f'<div style="font-size:0.7rem;color:var(--muted);margin-bottom:12px;">Suggestion {idx+1} of {total} · Line #{sug["line_index"]}</div>', unsafe_allow_html=True)

            # Original line
            st.markdown("**Original Line:**")
            st.markdown(f'<div class="line-before">{original}</div>', unsafe_allow_html=True)

            if reason:
                st.markdown(f'<div style="font-size:0.75rem;color:var(--muted);margin:8px 0;padding:6px 12px;border-left:2px solid var(--border);">💡 {reason}</div>', unsafe_allow_html=True)

            if keywords_added:
                kw_html = " ".join(f'<span class="keyword-chip missing">{k}</span>' for k in keywords_added)
                st.markdown(f"**Keywords being added:** {kw_html}", unsafe_allow_html=True)

            st.markdown("<br>**Choose a replacement (or skip):**", unsafe_allow_html=True)

            current_choice = st.session_state.choices_made.get(sug["line_index"])

            for i, opt in enumerate(options):
                char_diff = len(opt) - len(original)
                diff_str = f"+{char_diff}" if char_diff > 0 else str(char_diff)
                diff_color = "#c8472a" if abs(char_diff) > 20 else "#2a6fc8"
                selected = (current_choice == i)
                border = "2px solid var(--accent)" if selected else "1px solid var(--border)"

                col_opt, col_meta = st.columns([12, 1])
                with col_opt:
                    if st.button(f"Option {i+1}:  {opt}", key=f"opt_{idx}_{i}",
                                 use_container_width=True):
                        st.session_state.choices_made[sug["line_index"]] = i
                        st.session_state.suggestion_index = idx + 1
                        st.rerun()
                with col_meta:
                    st.markdown(f'<div style="font-size:0.65rem;color:{diff_color};padding-top:8px;">{diff_str} ch</div>', unsafe_allow_html=True)

            # Skip & nav
            col_s, col_prev, col_next = st.columns([3, 1, 1])
            with col_s:
                if st.button("Skip (keep original)", key=f"skip_{idx}"):
                    st.session_state.suggestion_index = idx + 1
                    st.rerun()
            with col_prev:
                if idx > 0:
                    if st.button("← Prev"):
                        st.session_state.suggestion_index = idx - 1
                        st.rerun()
            with col_next:
                if idx < total - 1:
                    if st.button("Next →"):
                        st.session_state.suggestion_index = idx + 1
                        st.rerun()

            # Sidebar summary
            with st.sidebar:
                st.markdown("### Review Progress")
                for i, s in enumerate(suggestions):
                    status = "✓" if s["line_index"] in st.session_state.choices_made else ("→" if i == idx else "○")
                    short = (s["original"][:40] + "…") if len(s["original"]) > 40 else s["original"]
                    st.markdown(f"`{status}` {short}")

# ── STEP 5: Download ──────────────────────────────────────────────────────────
elif st.session_state.step == 5:
    st.markdown("### Preview & Download")

    if st.session_state.final_docx_bytes is None:
        # No changes made — just export original with any manual choices
        with st.spinner("Building document…"):
            rp = st.session_state.resume_processor
            suggestions = st.session_state.suggestions
            for s in suggestions:
                chosen_idx = st.session_state.choices_made.get(s["line_index"], None)
                if chosen_idx is not None and chosen_idx < len(s["options"]):
                    rp.replace_line(s["line_index"], s["options"][chosen_idx])
            st.session_state.final_docx_bytes = rp.save_to_bytes()

    # Stats
    n_changed = len(st.session_state.choices_made)
    analysis = st.session_state.ats_analysis or {}
    old_score = analysis.get("ats_score", 0)
    new_score = min(100, old_score + n_changed * 4)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="metric-num">{n_changed}</div><div class="metric-label">Lines Changed</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="metric-num">{old_score}%</div><div class="metric-label">Original ATS Score</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="metric-num" style="color:var(--accent2);">{new_score}%</div><div class="metric-label">Estimated New Score</div></div>', unsafe_allow_html=True)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # Show what was changed
    if st.session_state.choices_made and st.session_state.suggestions:
        st.markdown("**Changes Applied:**")
        for s in st.session_state.suggestions:
            chosen_idx = st.session_state.choices_made.get(s["line_index"])
            if chosen_idx is not None:
                st.markdown(f'<div class="line-before">✗ {s["original"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="line-after">✓ {s["options"][chosen_idx]}</div>', unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="⬇ Download Tailored Resume (.docx)",
        data=st.session_state.final_docx_bytes,
        file_name="tailored_resume.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        use_container_width=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↺ Start Over with a New Resume"):
        for key in ["step","resume_processor","job_description","ats_analysis",
                    "suggestions","suggestion_index","choices_made","final_docx_bytes"]:
            st.session_state[key] = None if key not in ["step","suggestion_index"] else (1 if key=="step" else 0)
        st.session_state.choices_made = {}
        st.session_state.suggestions = []
        st.rerun()
