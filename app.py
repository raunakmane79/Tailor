import os
import tempfile
import subprocess
import shutil
import re

import streamlit as st

# ---------------------------------------------------
# PAGE CONFIG — must be first Streamlit call
# ---------------------------------------------------
st.set_page_config(
    page_title="Rizzume",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------
# GLOBAL CSS (fonts + base styles)
# ---------------------------------------------------
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,300;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
  :root {
    --bg: #05080f;
    --surface: #0b1120;
    --card: #0f1929;
    --border: rgba(255,255,255,0.09);
    --border2: rgba(255,255,255,0.16);
    --text: #e8edf5;
    --muted: #8a96a8;
    --subtle: #5a6373;
    --accent: #4f8bff;
    --accent2: #7ba7ff;
    --green: #22c55e;
    --amber: #f59e0b;
    --red: #ef4444;
    --font-head: 'Syne', sans-serif;
    --font-body: 'DM Sans', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    --r-sm: 10px;
    --r-md: 16px;
    --r-lg: 22px;
    --r-xl: 28px;
    --shadow: 0 20px 60px rgba(0,0,0,0.45);
  }

  html, body, [class*="css"] {
    font-family: var(--font-body) !important;
    color: var(--text) !important;
    background: var(--bg) !important;
  }

  /* Make the whole app background the login background */
  .stApp {
    background:
      radial-gradient(ellipse 80% 60% at 15% 5%, rgba(79,139,255,0.14) 0%, transparent 55%),
      radial-gradient(ellipse 60% 50% at 88% 90%, rgba(79,139,255,0.09) 0%, transparent 55%),
      #05080f !important;
    min-height: 100vh;
  }
 
  /* Strip ALL default streamlit padding/margin for login */
  .block-container {
    max-width: 480px !important;
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    margin: 0 auto !important;
  }
 
  header[data-testid="stHeader"] { display: none !important; }
  section[data-testid="stSidebar"] { display: none !important; }
  [data-testid="collapsedControl"] { display: none !important; }
  footer { display: none !important; }
   /* ---- LOGIN CARD ---- */
  .lcard {
    margin-top: max(6vh, 2.5rem);
    border-radius: 28px;
    padding: 2.5rem 2rem 2rem;
    background: linear-gradient(160deg, rgba(255,255,255,0.058), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow:
      0 40px 100px rgba(0,0,0,0.55),
      inset 0 1px 0 rgba(255,255,255,0.05);
    text-align: center;
  }
 
  .lmark {
    width: 54px;
    height: 54px;
    margin: 0 auto 1.3rem;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(79,139,255,0.24), rgba(79,139,255,0.07));
    border: 1px solid rgba(79,139,255,0.30);
    box-shadow: 0 8px 28px rgba(79,139,255,0.20);
    font-size: 1.45rem;
    color: #fff;
  }
 
  .ltitle {
    font-family: var(--font-head);
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -0.07em;
    color: #fff;
    line-height: 1;
    margin-bottom: 0.5rem;
  }
 
  .lsub {
    font-size: 0.87rem;
    color: #5d7290;
    line-height: 1.6;
    margin-bottom: 1.4rem;
  }
 
  .lpills {
    display: flex;
    justify-content: center;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-bottom: 1.6rem;
  }
 
  .lpill {
    padding: 0.28rem 0.58rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    color: #445566;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.03em;
  }
 
  .ldivider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07), transparent);
    margin-bottom: 1.5rem;
  }
 
  .alabel {
    display: block;
    text-align: left;
    font-size: 0.7rem;
    color: #4a6080;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.35rem;
    margin-top: 0.85rem;
  }
 
  /* Input fields */
  div[data-testid="stTextInput"] input {
    border-radius: 14px !important;
    min-height: 3rem !important;
    background: rgba(255,255,255,0.038) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: #edf3fb !important;
    box-shadow: none !important;
    padding-left: 1rem !important;
    font-size: 0.94rem !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
  }
 
  div[data-testid="stTextInput"] input:focus {
    border-color: rgba(79,139,255,0.48) !important;
    box-shadow: 0 0 0 3px rgba(79,139,255,0.1) !important;
    background: rgba(255,255,255,0.055) !important;
  }
 
  div[data-testid="stTextInput"] input::placeholder {
    color: #2d3d52 !important;
    opacity: 1 !important;
  }
 
  /* Hide the default Streamlit input label */
  div[data-testid="stTextInput"] label { display: none !important; }
 
  /* Submit button */
  div[data-testid="stFormSubmitButton"] > button {
    width: 100% !important;
    border-radius: 14px !important;
    min-height: 3.1rem !important;
    margin-top: 1.2rem !important;
    font-family: var(--font-body) !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border: none !important;
    background: linear-gradient(135deg, #2e62d9, #5590ff) !important;
    color: #fff !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 8px 28px rgba(79,139,255,0.22) !important;
    transition: all 0.18s ease !important;
  }
 
  div[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 14px 36px rgba(79,139,255,0.36) !important;
    filter: brightness(1.07) !important;
  }
 
  div[data-testid="stFormSubmitButton"] > button:active {
    transform: translateY(0px) !important;
  }
 
  .lnote {
    margin-top: 1.3rem;
    text-align: center;
    font-size: 0.74rem;
    color: #2a3a4d;
    letter-spacing: 0.03em;
  }
  /* ---------------- APP INPUTS ---------------- */

  div[data-testid="stTextInput"] input {
    border-radius: 14px !important;
    min-height: 3rem !important;
    background: #f8fafc !important;
    border: 1px solid rgba(15,23,42,0.14) !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    caret-color: #0f172a !important;
    box-shadow: none !important;
    padding-left: 1rem !important;
    font-size: 0.95rem !important;
    line-height: 1.4 !important;
  }

  div[data-testid="stTextInput"] input:focus {
    border-color: rgba(79,139,255,0.45) !important;
    box-shadow: 0 0 0 3px rgba(79,139,255,0.12) !important;
    background: #ffffff !important;
  }

  div[data-testid="stTextInput"] input::placeholder {
    color: #64748b !important;
    opacity: 1 !important;
  }

  div[data-testid="stTextArea"] textarea {
    border-radius: var(--r-md) !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    background: #f7f9fc !important;
    color: #0d1422 !important;
    -webkit-text-fill-color: #0d1422 !important;
    caret-color: #0d1422 !important;
    padding: 1rem !important;
    min-height: 280px !important;
    font-family: var(--font-body) !important;
    font-size: 0.96rem !important;
    line-height: 1.72 !important;
    box-shadow: none !important;
  }

  div[data-testid="stTextArea"] textarea::placeholder {
    color: #7a8694 !important;
    opacity: 1 !important;
  }

  div[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(79,139,255,0.5) !important;
    box-shadow: 0 0 0 4px rgba(79,139,255,0.14) !important;
    outline: none !important;
  }

  .stFileUploader label,
  .stTextArea label,
  label {
    font-family: var(--font-body) !important;
    color: #dde5f0 !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
  }

  div[data-testid="stFileUploader"] {
    border: 1.5px dashed rgba(255,255,255,0.14) !important;
    border-radius: var(--r-lg) !important;
    padding: 0.6rem !important;
    background: rgba(255,255,255,0.025) !important;
  }

  div[data-testid="stFileUploader"] section {
    background: transparent !important;
  }

  .stButton > button,
  .stDownloadButton > button {
    width: 100% !important;
    border-radius: var(--r-md) !important;
    min-height: 3rem !important;
    font-family: var(--font-body) !important;
    font-weight: 700 !important;
    font-size: 0.96rem !important;
    border: none !important;
    background: linear-gradient(135deg, #3a74f0, #5d95ff) !important;
    color: #fff !important;
    box-shadow: 0 10px 28px rgba(79,139,255,0.28);
    transition: all 0.18s ease !important;
  }

  .stButton > button:hover,
  .stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 14px 32px rgba(79,139,255,0.42) !important;
    filter: brightness(1.05) !important;
  }

  div[data-testid="stProgressBar"] > div {
    background: rgba(255,255,255,0.07) !important;
    border-radius: 999px !important;
    height: 10px !important;
  }

  div[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #3a74f0, #6fa8ff) !important;
    border-radius: 999px !important;
    transition: width 0.4s ease !important;
  }

  .topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 0.85rem 1.2rem;
    border-radius: var(--r-lg);
    margin-bottom: 1.2rem;
    background: rgba(11,17,32,0.85);
    border: 1px solid var(--border);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    position: sticky;
    top: 0.5rem;
    z-index: 100;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.9rem;
  }

  .brand-dot {
    width: 46px;
    height: 46px;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(79,139,255,0.25), rgba(79,139,255,0.07));
    border: 1px solid rgba(79,139,255,0.28);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.15rem;
    color: #fff;
    font-weight: 900;
  }

  .brand-name {
    font-family: var(--font-head);
    font-size: 1.15rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.04em;
    line-height: 1.05;
  }

  .brand-tagline {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 0.08rem;
  }

  .topbar-pills {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .tpill {
    padding: 0.44rem 0.76rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    color: #c8d4e3;
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 0.01em;
  }

  .hero {
    border-radius: var(--r-xl);
    padding: 2.2rem 2.2rem 2rem;
    background: linear-gradient(145deg, rgba(255,255,255,0.048), rgba(255,255,255,0.018));
    border: 1px solid var(--border);
    margin-bottom: 1.1rem;
    box-shadow: var(--shadow);
    overflow: hidden;
    position: relative;
  }

  .hero::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(circle at 18% 10%, rgba(79,139,255,0.15), transparent 40%);
  }

  .hero-grid {
    display: grid;
    grid-template-columns: 1.4fr 0.9fr;
    gap: 1.4rem;
    align-items: stretch;
  }

  .eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.38rem;
    padding: 0.4rem 0.72rem;
    border-radius: 999px;
    background: rgba(79,139,255,0.12);
    border: 1px solid rgba(79,139,255,0.22);
    color: #c4d8ff;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.9rem;
  }

  .hero-title {
    font-family: var(--font-head);
    font-size: clamp(2.6rem, 4.2vw, 4.4rem);
    font-weight: 800;
    letter-spacing: -0.07em;
    line-height: 0.95;
    color: #fff;
    margin: 0 0 0.9rem;
  }

  .hero-title .grad {
    background: linear-gradient(90deg, #4f8bff 0%, #a8c8ff 70%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .hero-body {
    font-size: 1.01rem;
    line-height: 1.82;
    color: #b8c8da;
    max-width: 580px;
    margin-bottom: 1rem;
  }

  .pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
  }

  .pill {
    padding: 0.52rem 0.85rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    color: #dce7f4;
    font-size: 0.82rem;
    font-weight: 600;
  }

  .stat-panel {
    border-radius: var(--r-lg);
    padding: 1.3rem;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
  }

  .stat-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
    color: var(--muted);
    margin-bottom: 0.4rem;
  }

  .stat-big {
    font-family: var(--font-head);
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -0.06em;
    color: #fff;
    line-height: 1;
  }

  .stat-copy {
    font-size: 0.93rem;
    color: #9fb5cc;
    line-height: 1.75;
    margin-top: 0.5rem;
  }

  .mini-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem;
    margin-top: 1rem;
  }

  .mini-box {
    border-radius: 14px;
    padding: 0.85rem;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    transition: all 0.2s;
  }

  .mini-box:hover {
    border-color: rgba(79,139,255,0.3);
    transform: translateY(-2px);
  }

  .mini-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 700;
    color: var(--muted);
    margin-bottom: 0.2rem;
  }

  .mini-val {
    font-size: 0.96rem;
    color: #fff;
    font-weight: 700;
  }

  .sec-card {
    border-radius: var(--r-xl);
    padding: 1.5rem 1.6rem;
    background: linear-gradient(160deg, rgba(255,255,255,0.046), rgba(255,255,255,0.018));
    border: 1px solid var(--border);
    margin-bottom: 1rem;
    box-shadow: 0 12px 35px rgba(0,0,0,0.2);
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .sec-card:hover {
    border-color: rgba(79,139,255,0.2);
    box-shadow: 0 16px 42px rgba(0,0,0,0.28);
  }

  .step-tag {
    display: inline-block;
    padding: 0.3rem 0.62rem;
    border-radius: 999px;
    background: rgba(79,139,255,0.1);
    border: 1px solid rgba(79,139,255,0.2);
    color: #c5daff;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 0.7rem;
  }

  .sec-title {
    font-family: var(--font-head);
    font-size: 1.3rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.03em;
    margin-bottom: 0.2rem;
  }

  .sec-sub {
    font-size: 0.94rem;
    color: #9aacbf;
    line-height: 1.72;
  }

  .metric-shell {
    border-radius: var(--r-lg);
    padding: 1.1rem 1.15rem;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    transition: all 0.22s;
  }

  .metric-shell:hover {
    border-color: rgba(79,139,255,0.24);
    transform: translateY(-2px);
  }

  [data-testid="metric-container"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
  }

  [data-testid="metric-container"] label {
    font-family: var(--font-body) !important;
    color: var(--muted) !important;
    font-weight: 700 !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.09em;
  }

  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: var(--font-head) !important;
    color: #fff !important;
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.04em !important;
  }

  .kw-box {
    border-radius: var(--r-lg);
    padding: 1.05rem 1.1rem;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    min-height: 180px;
  }

  .kw-title {
    font-weight: 700;
    font-size: 0.97rem;
    color: #e2eaf4;
    margin-bottom: 0.75rem;
  }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.48rem;
  }

  .chip-ok {
    background: rgba(34,197,94,0.12);
    color: #bbf7d0;
    border: 1px solid rgba(34,197,94,0.24);
    padding: 0.38rem 0.68rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
  }

  .chip-miss {
    background: rgba(245,158,11,0.12);
    color: #fde68a;
    border: 1px solid rgba(245,158,11,0.24);
    padding: 0.38rem 0.68rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
  }

  .req-item {
    padding: 0.85rem 1rem;
    border-radius: var(--r-sm);
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    color: #cdd8e7;
    font-size: 0.94rem;
    line-height: 1.68;
    margin-bottom: 0.6rem;
  }

  .sug-card {
    border-radius: var(--r-lg);
    padding: 1.1rem 1.15rem;
    margin-bottom: 0.9rem;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    transition: border-color 0.2s;
  }

  .sug-card:hover {
    border-color: rgba(79,139,255,0.2);
  }

  .line-label {
    font-size: 0.73rem;
    color: var(--muted);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 0.42rem;
  }

  .reason-box {
    background: rgba(79,139,255,0.08);
    border: 1px solid rgba(79,139,255,0.18);
    border-radius: 12px;
    padding: 0.85rem 1rem;
    color: #c8daff;
    margin: 0.75rem 0;
    font-size: 0.93rem;
    line-height: 1.65;
  }

  div[role="radiogroup"] > label {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-md) !important;
    padding: 0.9rem 1rem !important;
    margin-bottom: 0.6rem !important;
    transition: all 0.18s ease !important;
    min-height: 58px !important;
  }

  div[role="radiogroup"] > label:hover {
    border-color: rgba(79,139,255,0.34) !important;
    background: rgba(79,139,255,0.05) !important;
    transform: translateY(-1px) !important;
  }

  div[role="radiogroup"] > label p,
  div[role="radiogroup"] > label span,
  div[role="radiogroup"] > label div {
    color: #dce8f5 !important;
    font-family: var(--font-body) !important;
    font-size: 0.96rem !important;
    line-height: 1.6 !important;
  }

  div[data-testid="stCodeBlock"] {
    border-radius: 14px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
  }

  div[data-testid="stCodeBlock"] pre,
  div[data-testid="stCodeBlock"] code {
    font-family: var(--font-mono) !important;
    white-space: pre-wrap !important;
    word-break: break-word !important;
    font-size: 0.88rem !important;
    line-height: 1.65 !important;
  }

  .load-wrap { margin: 0.5rem 0 1.2rem; }
  .load-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .load-label {
    font-size: 0.86rem;
    font-weight: 600;
    color: var(--muted);
  }

  .load-pct {
    font-family: var(--font-head);
    font-size: 1.1rem;
    font-weight: 800;
    color: var(--accent2);
    letter-spacing: -0.03em;
  }

  .load-track {
    width: 100%;
    height: 8px;
    border-radius: 999px;
    background: rgba(255,255,255,0.07);
    overflow: hidden;
  }

  .load-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #3a74f0, #6fa8ff);
    transition: width 0.5s cubic-bezier(.4,0,.2,1);
    box-shadow: 0 0 12px rgba(79,139,255,0.5);
  }

  .dl-card {
    border-radius: var(--r-xl);
    padding: 1.5rem 1.6rem;
    background: linear-gradient(145deg, rgba(79,139,255,0.08), rgba(79,139,255,0.025));
    border: 1px solid rgba(79,139,255,0.18);
    margin-top: 0.8rem;
    box-shadow: 0 12px 32px rgba(0,0,0,0.2);
  }

  .dl-title {
    font-family: var(--font-head);
    font-size: 1.1rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 0.25rem;
    letter-spacing: -0.03em;
  }

  .dl-sub {
    font-size: 0.88rem;
    color: var(--muted);
    margin-bottom: 1.1rem;
  }

  .success-bar {
    padding: 0.88rem 1rem;
    border-radius: 14px;
    background: rgba(34,197,94,0.1);
    border: 1px solid rgba(34,197,94,0.2);
    color: #bbf7d0;
    font-size: 0.92rem;
    font-weight: 500;
    margin-bottom: 0.9rem;
  }

  .empty-card {
    padding: 1.3rem;
    border-radius: var(--r-lg);
    text-align: center;
    background: rgba(255,255,255,0.025);
    border: 1px dashed var(--border);
    color: var(--muted);
    font-size: 0.94rem;
    margin-top: 0.5rem;
  }

  .footer-note {
    text-align: center;
    color: var(--subtle);
    margin-top: 1.5rem;
    font-size: 0.87rem;
  }

  div[data-baseweb="notification"] {
    border-radius: 16px !important;
  }

  @media (max-width: 1000px) {
    .hero-grid { grid-template-columns: 1fr; }
    .topbar { flex-direction: column; align-items: flex-start; }
  }
</style>
""",
    unsafe_allow_html=True,
)
# ---------------------------------------------------
# PASSWORD GATE
# ---------------------------------------------------
def check_password():
    if st.session_state.get("_auth"):
        return True

    def _authenticate():
        entered_password = st.session_state.get("pw_input", "")
        if entered_password == st.secrets.get("APP_PASSWORD", ""):
            st.session_state["_auth"] = True
            st.session_state["_auth_fail"] = False
            st.rerun()
        else:
            st.session_state["_auth_fail"] = True

    st.markdown(
        """
        <div class="lcard">
          <div class="lmark">✦</div>
          <div class="ltitle">Rizzume</div>
          <div class="lsub"></div>
    
          <div class="ldivider"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False, enter_to_submit=True):
        st.markdown('<span class="alabel">Login ID</span>', unsafe_allow_html=True)
        st.text_input("Login ID", key="login_id_input", label_visibility="collapsed", placeholder="Enter ID")

        st.markdown('<span class="alabel">Password</span>', unsafe_allow_html=True)
        st.text_input("Password", type="password", key="pw_input", label_visibility="collapsed", placeholder="••••••••••")

        submitted = st.form_submit_button("Enter Workspace  ✦", use_container_width=True)
        if submitted:
            _authenticate()

    if st.session_state.get("_auth_fail"):
        st.error("Incorrect password. Please try again.")

    st.markdown('<div class="lnote">Private workspace · Authorized access only</div>', unsafe_allow_html=True)
    return False


if not check_password():
    st.stop()

# ---------------------------------------------------
# After auth: restore full-width layout
# ---------------------------------------------------
st.markdown("""
<style>
  .block-container {
    max-width: 100% !important;
    padding: 1rem 1.5rem !important;
  }
  header[data-testid="stHeader"] { display: block !important; background: transparent !important; }
</style>
""", unsafe_allow_html=True)
# ---------------------------------------------------
# REMAINING IMPORTS (only after auth)
# ---------------------------------------------------
from resume_processor import ResumeProcessor
from gemini_client import GeminiClient

# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------
def reset_state_for_new_file():
    for k in [
        "ats_analysis",
        "suggestions",
        "choices_made",
        "pdf_bytes",
        "tailored_docx_bytes",
        "line_edits",
        "ready_for_manual_edit",
    ]:
        if k == "suggestions":
            st.session_state[k] = []
        elif k == "choices_made":
            st.session_state[k] = {}
        elif k == "line_edits":
            st.session_state[k] = {}
        elif k == "ready_for_manual_edit":
            st.session_state[k] = False
        else:
            st.session_state[k] = None


def full_reset():
    for k in [
        "resume_processor",
        "ats_analysis",
        "suggestions",
        "choices_made",
        "pdf_bytes",
        "tailored_docx_bytes",
        "uploaded_filename",
        "uploaded_file_signature",
        "line_edits",
        "ready_for_manual_edit",
    ]:
        st.session_state[k] = None
    st.session_state["suggestions"] = []
    st.session_state["choices_made"] = {}
    st.session_state["line_edits"] = {}
    st.session_state["ready_for_manual_edit"] = False


def show_empty_state(msg):
    st.markdown(f'<div class="empty-card">{msg}</div>', unsafe_allow_html=True)


def extract_name_from_resume(lines):
    for line in lines:
        text = line["text"].strip()
        words = text.split()
        if len(words) >= 2:
            return f"{words[0]}_{words[1]}"
    return "Candidate"


def extract_job_title(jd):
    lines = jd.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if len(line) < 80 and not line.lower().startswith(("about", "we", "company")):
            return re.sub(r"[^\w\s]", "", line).replace(" ", "_")
    return "Role"


def convert_docx_to_pdf_bytes(docx_bytes):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_docx = os.path.join(tmpdir, "resume.docx")
        output_pdf = os.path.join(tmpdir, "resume.pdf")
        with open(input_docx, "wb") as f:
            f.write(docx_bytes)

        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", input_docx, "--outdir", tmpdir],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice failed.\n{result.stdout}\n{result.stderr}")
        if not os.path.exists(output_pdf):
            raise RuntimeError("PDF not created.")

        with open(output_pdf, "rb") as f:
            return f.read()


SOFFICE_AVAILABLE = shutil.which("soffice") is not None

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error("GEMINI_API_KEY not found in Streamlit secrets.")
    st.stop()

client = GeminiClient(GEMINI_API_KEY)

# ---------------------------------------------------
# SESSION STATE DEFAULTS
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
    "_loading_stage": None,
    "_loading_pct": 0,
    "line_edits": {},
    "line_char_limit": 90,
    "ready_for_manual_edit": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------
# LOADING BAR HELPER
# ---------------------------------------------------
def render_loading_bar(label, pct):
    st.markdown(
        f"""
<div class="load-wrap">
  <div class="load-header">
    <span class="load-label">{label}</span>
    <span class="load-pct">{pct}%</span>
  </div>
  <div class="load-track">
    <div class="load-fill" style="width:{pct}%"></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------
# TOP BAR
# ---------------------------------------------------
st.markdown(
    """
<div class="topbar">
  <div class="brand">
    <div class="brand-dot">✦</div>
    <div>
      <div class="brand-name">Rizzume</div>
      <div class="brand-tagline">Resume tailoring that ships sharp, clean, and recruiter-ready</div>
    </div>
  </div>
  <div class="topbar-pills">
    <div class="tpill">ATS Match</div>
    <div class="tpill">Format Safe</div>
    <div class="tpill">DOCX + PDF</div>
    <div class="tpill">Inline Editor</div>
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
<div class="hero">
  <div class="hero-grid">
    <div>
      <div class="eyebrow">✦ Smarter Resume Tailoring</div>
      <div class="hero-title"><span class="grad">Rizzume</span><br>Rizz up your recruiter</div>
      <div class="hero-body">Upload your resume, paste the job description, and tailor each line without breaking the format. Spot keyword gaps, get sharper rewrites, edit after selection, and export a clean final version.</div>
      <div class="pill-row">
        <div class="pill">ATS Analysis</div>
        <div class="pill">Keyword Match</div>
        <div class="pill">Line Rewrites</div>
        <div class="pill">Keyword Reference</div>
        <div class="pill">Export Ready</div>
      </div>
    </div>
    <div class="stat-panel">
      <div>
        <div class="stat-label">What it does</div>
        <div class="stat-big">Tailor faster</div>
        <div class="stat-copy">Review ATS gaps, accept the best rewrites, then manually fine-tune the updated resume with keyword guidance on the side.</div>
      </div>
      <div class="mini-grid">
        <div class="mini-box"><div class="mini-label">Focus</div><div class="mini-val">ATS + Clarity</div></div>
        <div class="mini-box"><div class="mini-label">Brand</div><div class="mini-val">Rizzume ✦</div></div>
      </div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------
# WORKFLOW PROGRESS
# ---------------------------------------------------
steps = 0
if st.session_state.resume_processor:
    steps = 1
if st.session_state.ats_analysis:
    steps = 2
if st.session_state.suggestions:
    steps = 3
if st.session_state.ready_for_manual_edit:
    steps = 4

labels = ["Upload", "ATS Analysis", "Suggestions", "Edit & Export"]
render_loading_bar(f"Workflow — {labels[min(steps, 3)]}", int(steps / 4 * 100))

# ---------------------------------------------------
# STEP 1 — INPUTS
# ---------------------------------------------------
st.markdown(
    """
<div class="sec-card">
  <div class="step-tag">Step 01</div>
  <div class="sec-title">Upload Resume & Job Description</div>
  <div class="sec-sub">Start with your DOCX resume and the role you want to target.</div>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1.35], gap="large")

with left:
    uploaded_file = st.file_uploader("Upload your resume (.docx)", type=["docx"])

with right:
    job_description = st.text_area(
        "Paste Job Description",
        height=280,
        placeholder="Paste the full job description here…",
    )

if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    sig = (uploaded_file.name, len(file_bytes))
    if st.session_state.uploaded_file_signature != sig:
        st.session_state.resume_processor = ResumeProcessor(file_bytes)
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.uploaded_file_signature = sig
        reset_state_for_new_file()
        st.markdown(
            '<div class="success-bar">✅ Resume uploaded successfully. Ready to analyze.</div>',
            unsafe_allow_html=True,
        )

u1, u2, _ = st.columns([1, 1, 4], gap="large")

with u1:
    if st.button("Analyze ATS Match", use_container_width=True):
        if st.session_state.resume_processor is None:
            st.warning("Please upload a resume first.")
        elif not job_description.strip():
            st.warning("Please paste the job description.")
        else:
            resume_text = "\n".join(
                l["text"] for l in st.session_state.resume_processor.get_all_lines() if l["text"].strip()
            )
            render_loading_bar("Running ATS analysis…", 25)
            with st.spinner(""):
                try:
                    ats = client.analyze_ats(resume_text, job_description)
                    st.session_state.ats_analysis = ats
                    st.session_state.suggestions = []
                    st.session_state.choices_made = {}
                    st.session_state.tailored_docx_bytes = None
                    st.session_state.pdf_bytes = None
                    st.session_state.ready_for_manual_edit = False
                    render_loading_bar("ATS analysis complete", 50)
                    st.success("ATS analysis complete.")
                except Exception as e:
                    st.error(f"ATS analysis failed: {e}")

with u2:
    if st.button("Reset", use_container_width=True):
        full_reset()
        st.rerun()

if st.session_state.resume_processor is not None:
    with st.expander("Preview extracted resume lines"):
        for line in st.session_state.resume_processor.get_all_lines():
            if line["text"].strip():
                st.write(f'**[{line["index"]}]** · {line["char_count"]} chars')
                st.code(line["text"])

# ---------------------------------------------------
# STEP 2 — ATS
# ---------------------------------------------------
if st.session_state.resume_processor:
    st.markdown(
        """
<div class="sec-card">
  <div class="step-tag">Step 02</div>
  <div class="sec-title">ATS Match Analysis</div>
  <div class="sec-sub">Review ATS score, missing keywords, and job requirements before generating rewrite suggestions.</div>
</div>
""",
        unsafe_allow_html=True,
    )

if not st.session_state.ats_analysis and st.session_state.resume_processor:
    show_empty_state("Run analysis to unlock ATS score, keyword coverage, and rewrite suggestions ✦")

if st.session_state.ats_analysis:
    ats = st.session_state.ats_analysis
    ats_score = int(ats.get("ats_score", 0))
    confidence = "High" if ats_score >= 80 else ("Medium" if ats_score >= 60 else "Low")

    c1, c2, c3, c4 = st.columns(4, gap="large")
    for col, label, val in [
        (c1, "ATS Score", f"{ats_score}%"),
        (c2, "Present Keywords", str(len(ats.get("present_keywords", [])))),
        (c3, "Missing Keywords", str(len(ats.get("missing_keywords", [])))),
        (c4, "Confidence", confidence),
    ]:
        with col:
            st.markdown('<div class="metric-shell">', unsafe_allow_html=True)
            st.metric(label, val)
            st.markdown('</div>', unsafe_allow_html=True)

    if ats.get("score_note"):
        st.info(ats["score_note"])

    kw1, kw2 = st.columns(2, gap="large")
    with kw1:
        present = ats.get("present_keywords", [])
        html = "".join(f'<span class="chip-ok">{k}</span>' for k in present) or '<span style="color:var(--muted)">None detected.</span>'
        st.markdown(
            f'<div class="kw-box"><div class="kw-title">✓ Present Keywords</div><div class="chip-row">{html}</div></div>',
            unsafe_allow_html=True,
        )
    with kw2:
        missing = ats.get("missing_keywords", [])
        html = "".join(f'<span class="chip-miss">{k}</span>' for k in missing) or '<span style="color:var(--muted)">None missing!</span>'
        st.markdown(
            f'<div class="kw-box"><div class="kw-title">⚠ Missing Keywords</div><div class="chip-row">{html}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Key Requirements")
    for req in ats.get("key_requirements", []):
        st.markdown(f'<div class="req-item">→ {req}</div>', unsafe_allow_html=True)

    st.markdown("### Formatting Control")
    preset_col, slider_col = st.columns([1, 2], gap="large")

    with preset_col:
        char_preset = st.selectbox(
            "Preset",
            ["Compact", "Balanced", "Relaxed"],
            index=1,
            help="A quick way to set your target characters per visual line.",
        )

    preset_map = {"Compact": 80, "Balanced": 90, "Relaxed": 100}
    default_slider_value = st.session_state.get("line_char_limit", preset_map[char_preset])

    with slider_col:
        line_char_limit = st.slider(
            "Target characters per visual line",
            min_value=60,
            max_value=130,
            value=default_slider_value if default_slider_value in range(60, 131) else preset_map[char_preset],
            step=5,
            help="If an original bullet fits within this limit, AI keeps it within one line. If the original bullet exceeds this limit, AI can use up to two lines.",
        )

    if st.session_state.get("line_char_limit") != line_char_limit:
        st.session_state.line_char_limit = line_char_limit

    st.caption(
        f"Current rule: bullets up to {st.session_state.line_char_limit} chars are treated as one-line bullets. "
        f"Longer bullets can use up to {st.session_state.line_char_limit * 2} chars."
    )

def is_heading_like(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True

    t_low = t.lower().strip(":").strip()
    heading_words = {
        "education",
        "experience",
        "work experience",
        "projects",
        "skills",
        "technical skills",
        "leadership",
        "activities",
        "summary",
        "profile",
        "certifications",
        "awards",
        "contact",
        "professional experience",
    }

    if t_low in heading_words:
        return True

    if len(t) <= 4:
        return True

    if len(t.split()) <= 5 and t.upper() == t:
        return True

    return False


gen_c1, _ = st.columns([1, 4], gap="large")
with gen_c1:
    if st.button("Generate Suggestions", use_container_width=True):
        lines = st.session_state.resume_processor.get_all_lines(include_empty=False)
        render_loading_bar("Generating AI rewrites…", 65)

        with st.spinner(""):
            try:
                target_keywords = (
                    ats.get("high_priority_missing")
                    or ats.get("recommended_keyword_targets")
                    or ats.get("missing_keywords")
                    or []
                )

                candidate_lines = []
in_skills_section = False

for line in lines:
    text = line.get("text", "").strip()
    if not text:
        continue

    lower = text.lower().strip(":").strip()

    if lower in {"skills", "technical skills"}:
        in_skills_section = True
        continue

    if lower in {"education", "experience", "work experience", "projects", "leadership", "activities"}:
        in_skills_section = False

    if is_heading_like(text):
        continue

    if len(text) < 8:
        continue

    if is_position_or_title_like(text):
        continue

    if is_project_title_like(text) and not in_skills_section:
        continue

    line["section_hint"] = "skills" if in_skills_section else "general"
    candidate_lines.append(line)

                sugs = client.generate_suggestions(
                    lines=candidate_lines,
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

                render_loading_bar("Suggestions ready", 75)

                if sugs:
                    st.success(f"Generated {len(sugs)} suggestion(s).")
                else:
                    st.warning("No suggestions returned.")

            except Exception as e:
                st.error(f"Generation failed: {e}")

# ---------------------------------------------------
# STEP 3 — SUGGESTIONS
# ---------------------------------------------------
if st.session_state.ats_analysis and not st.session_state.suggestions:
    show_empty_state("ATS analysis ready. Generate suggestions to review line-by-line rewrites.")

if st.session_state.suggestions:
    st.markdown(
        """
<div class="sec-card">
  <div class="step-tag">Step 03</div>
  <div class="sec-title">Generated Suggestions</div>
  <div class="sec-sub">Pick the rewrites you want first. After applying them, the manual editor will open with those changes already included.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    total = len(st.session_state.suggestions)
    chosen = len(st.session_state.choices_made)
    render_loading_bar(f"Selections made: {chosen}/{total}", int(chosen / total * 100) if total else 0)

    for i, sug in enumerate(st.session_state.suggestions):
        li = sug.get("line_index", "?")
        original = sug.get("original", "")
        options = sug.get("options", [])
        reason = sug.get("reason", "")
        char_budget = sug.get("char_budget")

        st.markdown('<div class="sug-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="line-label">Resume Line {li}</div>', unsafe_allow_html=True)
        st.code(original, language=None)

        if char_budget:
            st.caption(f"Allowed length for this line: up to {char_budget} characters")

        if reason:
            st.markdown(
                f'<div class="reason-box"><strong>Why flagged:</strong> {reason}</div>',
                unsafe_allow_html=True,
            )

        radio_opts = ["Keep original"] + options
        cur = st.session_state.choices_made.get(i, "Keep original")
        sel = st.radio(
            f"Line {li}",
            radio_opts,
            index=radio_opts.index(cur) if cur in radio_opts else 0,
            key=f"r_{i}",
            label_visibility="collapsed",
        )

        if sel == "Keep original":
            st.session_state.choices_made.pop(i, None)
        else:
            st.session_state.choices_made[i] = sel

        st.markdown('</div>', unsafe_allow_html=True)

    ap1, _ = st.columns([1, 4], gap="large")
    with ap1:
        if st.button("Apply Selected Changes & Open Editor", use_container_width=True):
            if st.session_state.resume_processor is None:
                st.error("Resume processor not found. Re-upload your resume.")
            else:
                try:
                    fresh_proc = ResumeProcessor(uploaded_file.getvalue()) if uploaded_file else ResumeProcessor(
                        st.session_state.resume_processor.export()
                    )

                    for i, sug in enumerate(st.session_state.suggestions):
                        chosen_text = st.session_state.choices_made.get(i)
                        if chosen_text:
                            fresh_proc.replace_line(sug["line_index"], chosen_text)

                    st.session_state.resume_processor = fresh_proc
                    st.session_state.tailored_docx_bytes = fresh_proc.export()
                    st.session_state.pdf_bytes = None
                    st.session_state.line_edits = {}

                    for line in st.session_state.resume_processor.get_all_lines():
                        if line["text"].strip():
                            st.session_state.line_edits[line["index"]] = line["text"]

                    st.session_state.ready_for_manual_edit = True
                    render_loading_bar("Suggestions applied — editor ready", 90)
                    st.success("Selected suggestions applied. You can now manually edit the updated resume below.")
                except Exception as e:
                    st.error(f"Failed to apply changes: {e}")

# ---------------------------------------------------
# STEP 4 — INLINE EDITOR + EXPORT
# ---------------------------------------------------
if st.session_state.resume_processor is not None and st.session_state.ready_for_manual_edit:
    lines = st.session_state.resume_processor.get_all_lines()
    name_part = extract_name_from_resume(lines)
    job_part = extract_job_title(job_description if job_description else "")
    file_stem = f"{name_part}_{job_part}_Resume"
    ats = st.session_state.ats_analysis or {}

    st.markdown(
        """
<div class="sec-card">
  <div class="step-tag">Step 04</div>
  <div class="sec-title">Manual Edit & Export</div>
  <div class="sec-sub">
    Your selected suggestions have already been applied. Make final manual edits, refer to ATS keywords on the side, and then download your DOCX.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    edit_col, keyword_col = st.columns([2.2, 1], gap="large")

    with edit_col:
        st.markdown(
            """
<div style="background:rgba(79,139,255,0.06);border:1px solid rgba(79,139,255,0.16);
            border-radius:16px;padding:1rem 1.2rem;margin-bottom:1rem;">
  <span style="font-size:0.85rem;color:#a8c4ff;font-weight:600;">
    ✏️ Edit the already-updated resume below, then click <strong>Apply Manual Edits → Rebuild DOCX</strong>.
  </span>
</div>
""",
            unsafe_allow_html=True,
        )

        all_lines = st.session_state.resume_processor.get_all_lines()
        editable_lines = [l for l in all_lines if l["text"].strip()]

        st.markdown(
            '<div style="border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;margin-bottom:1rem;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="background:#1a2236;padding:0.65rem 1.1rem;border-bottom:1px solid rgba(255,255,255,0.07);">'
            '<span style="font-size:0.75rem;font-weight:700;color:#7a90b0;text-transform:uppercase;letter-spacing:0.09em;">'
            'Line Editor — updated resume</span></div>',
            unsafe_allow_html=True,
        )

        for l in editable_lines:
            idx = l["index"]
            col_idx, col_edit = st.columns([0.08, 0.92], gap="small")
            with col_idx:
                st.markdown(
                    f'<div style="padding:0.55rem 0;text-align:center;font-size:0.72rem;'
                    f'font-weight:700;color:#4a5a72;font-family:var(--font-mono);">{idx}</div>',
                    unsafe_allow_html=True,
                )
            with col_edit:
                new_val = st.text_input(
                    label=f"line_{idx}",
                    value=st.session_state.line_edits.get(idx, l["text"]),
                    key=f"le_{idx}",
                    label_visibility="collapsed",
                )
                st.session_state.line_edits[idx] = new_val

        st.markdown('</div>', unsafe_allow_html=True)

        apply_col, _ = st.columns([1, 3], gap="large")
        with apply_col:
            if st.button("✅ Apply Manual Edits → Rebuild DOCX", use_container_width=True):
                try:
                    if uploaded_file is not None:
                        fresh_proc = ResumeProcessor(uploaded_file.getvalue())
                    else:
                        fresh_proc = ResumeProcessor(st.session_state.resume_processor.export())

                    for i, sug in enumerate(st.session_state.suggestions):
                        chosen_text = st.session_state.choices_made.get(i)
                        if chosen_text:
                            fresh_proc.replace_line(sug["line_index"], chosen_text)

                    original_current_lines = st.session_state.resume_processor.get_all_lines()

                    for idx, new_text in st.session_state.line_edits.items():
                        original_text = next(
                            (l["text"] for l in original_current_lines if l["index"] == idx), None
                        )
                        if original_text is not None and new_text != original_text:
                            fresh_proc.replace_line(idx, new_text)

                    st.session_state.resume_processor = fresh_proc
                    st.session_state.tailored_docx_bytes = fresh_proc.export()
                    st.session_state.pdf_bytes = None

                    for line in st.session_state.resume_processor.get_all_lines():
                        if line["text"].strip():
                            st.session_state.line_edits[line["index"]] = line["text"]

                    render_loading_bar("DOCX rebuilt with manual edits — ready to export", 95)
                    st.success("DOCX rebuilt. Download buttons below are now up to date.")
                except Exception as e:
                    st.error(f"Failed to rebuild DOCX: {e}")

    with keyword_col:
        present = ats.get("present_keywords", [])
        missing = ats.get("missing_keywords", [])
        recommended = (
            ats.get("high_priority_missing", [])
            or ats.get("recommended_keyword_targets", [])
            or []
        )

        st.markdown(
            """
<div class="sec-card" style="padding:1.15rem;">
  <div class="sec-title" style="font-size:1.05rem;">Keyword Reference</div>
  <div class="sec-sub" style="font-size:0.86rem;">Use these while manually editing the updated resume.</div>
</div>
""",
            unsafe_allow_html=True,
        )

        html = "".join(f'<span class="chip-miss">{k}</span>' for k in recommended) or '<span style="color:var(--muted)">None</span>'
        st.markdown(f'<div class="kw-box"><div class="kw-title">Priority Keywords</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

        html = "".join(f'<span class="chip-miss">{k}</span>' for k in missing) or '<span style="color:var(--muted)">None</span>'
        st.markdown(f'<div class="kw-box" style="margin-top:1rem;"><div class="kw-title">All Missing Keywords</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

        html = "".join(f'<span class="chip-ok">{k}</span>' for k in present) or '<span style="color:var(--muted)">None</span>'
        st.markdown(f'<div class="kw-box" style="margin-top:1rem;"><div class="kw-title">Already Present</div><div class="chip-row">{html}</div></div>', unsafe_allow_html=True)

    current_docx = (
        st.session_state.tailored_docx_bytes
        if st.session_state.tailored_docx_bytes is not None
        else st.session_state.resume_processor.export()
    )

    st.markdown(
        """
<div class="dl-card">
  <div class="dl-title">Export Your Tailored Resume</div>
  <div class="dl-sub">
    Your selected suggestions and manual edits are now included. Download the updated DOCX below.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    d1, d2, d3 = st.columns(3, gap="large")

    with d1:
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#8a9eb8;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;">Word Document</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            label="⬇ Download DOCX",
            data=current_docx,
            file_name=f"{file_stem}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        st.markdown(
            '<div style="font-size:0.78rem;color:#5a6880;margin-top:0.4rem;line-height:1.5;">'
            'Selected suggestions + manual edits included.</div>',
            unsafe_allow_html=True,
        )

    with d2:
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#8a9eb8;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;">PDF Export</div>',
            unsafe_allow_html=True,
        )
        if SOFFICE_AVAILABLE:
            if st.button("⚙ Generate PDF", use_container_width=True):
                render_loading_bar("Converting to PDF…", 85)
                with st.spinner(""):
                    try:
                        st.session_state.pdf_bytes = convert_docx_to_pdf_bytes(current_docx)
                        render_loading_bar("PDF ready!", 100)
                        st.success("PDF ready to download.")
                    except Exception as e:
                        st.error(f"PDF conversion failed: {e}")

            if st.session_state.pdf_bytes:
                st.download_button(
                    label="⬇ Download PDF",
                    data=st.session_state.pdf_bytes,
                    file_name=f"{file_stem}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.markdown(
                    '<div style="font-size:0.78rem;color:#5a6880;margin-top:0.4rem;line-height:1.5;">'
                    'Click Generate PDF first.</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div style="font-size:0.84rem;color:#5a6880;padding:0.6rem 0;line-height:1.6;">'
                'PDF export unavailable — LibreOffice not installed on this deployment.</div>',
                unsafe_allow_html=True,
            )

    with d3:
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:700;color:#8a9eb8;'
            'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem;">Google Docs</div>',
            unsafe_allow_html=True,
        )

        gdocs_html = """
<div style="background:rgba(79,139,255,0.07);border:1px solid rgba(79,139,255,0.18);
            border-radius:16px;padding:1rem 1.1rem;">
  <ol style="font-size:0.83rem;color:#9ab0cc;line-height:1.8;margin:0 0 0.85rem 1.1rem;padding:0;">
    <li>Download the <strong style="color:#c5daff">DOCX</strong></li>
    <li>Open Google Drive upload</li>
    <li>Upload and open with Google Docs</li>
  </ol>
  <a href="https://drive.google.com/drive/my-drive?action=newfile" target="_blank"
     style="display:flex;align-items:center;justify-content:center;gap:0.5rem;
            padding:0.7rem 1rem;border-radius:12px;
            background:linear-gradient(135deg,#3a74f0,#5d95ff);color:#fff;
            font-size:0.88rem;font-weight:700;text-decoration:none;
            box-shadow:0 6px 18px rgba(79,139,255,0.32);transition:all 0.15s;">
    Open Google Drive Upload ↗
  </a>
</div>
"""
        st.markdown(gdocs_html, unsafe_allow_html=True)

    render_loading_bar("All done — resume tailored ✦", 100)

st.markdown(
    '<div class="footer-note">Rizzume ✦ — review suggestions, edit the updated resume, then export cleanly.</div>',
    unsafe_allow_html=True,
)
