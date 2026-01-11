"""
Trap - FOG / Grease Trap Invoice & Manifest Parser
A modern web application built with Streamlit.
"""

import base64
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src/ to path for engine imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
from trap.parse import EXPECTED_FIELDS, parse_text_to_record

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Trap - FOG Invoice Parser",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- PATHS ---
ASSETS_DIR = Path(__file__).parent / "assets"
VIDEO_PATH = ASSETS_DIR / "bg.mp4"
FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"


# --- BACKGROUND ---
def inject_background():
    """Inject video background if available, otherwise gradient."""
    if VIDEO_PATH.exists():
        video_b64 = base64.b64encode(VIDEO_PATH.read_bytes()).decode()
        st.markdown(f"""
        <style>
            #video-bg {{
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                z-index: -1;
                overflow: hidden;
                pointer-events: none;
            }}
            #video-bg video {{
                position: absolute;
                top: 50%; left: 50%;
                min-width: 100%; min-height: 100%;
                transform: translate(-50%, -50%);
                object-fit: cover;
            }}
            #video-bg .overlay {{
                position: absolute;
                top: 0; left: 0;
                width: 100%; height: 100%;
                background: rgba(15, 23, 42, 0.75);
            }}
        </style>
        <div id="video-bg">
            <video autoplay muted loop playsinline>
                <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
            </video>
            <div class="overlay"></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            #gradient-bg {
                position: fixed;
                top: 0; left: 0;
                width: 100vw; height: 100vh;
                z-index: -1;
                background: linear-gradient(-45deg, #0f172a, #1e1b4b, #172554, #0c4a6e);
                background-size: 400% 400%;
                animation: gradientMove 20s ease infinite;
            }
            @keyframes gradientMove {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
        </style>
        <div id="gradient-bg"></div>
        """, unsafe_allow_html=True)


# --- STYLES ---
def inject_styles():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {
            --primary: #6366f1;
            --accent: #22d3ee;
            --bg-glass: rgba(30, 41, 59, 0.7);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --border: rgba(148, 163, 184, 0.2);
        }

        .stApp {
            font-family: 'Inter', sans-serif;
            background: transparent !important;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"],
        .main .block-container {
            background: transparent !important;
        }

        #MainMenu, footer, header { visibility: hidden; }
        .stDeployButton { display: none; }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            border-right: 1px solid var(--border);
        }

        .glass-card {
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid var(--border);
            padding: 2.5rem;
            margin-bottom: 2rem;
        }

        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, #22d3ee 50%, #6366f1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }

        .hero-subtitle {
            font-size: 1.25rem;
            color: var(--text-secondary);
        }

        .section-title {
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }

        .stButton > button {
            background: linear-gradient(135deg, var(--primary) 0%, #4f46e5 100%);
            color: white;
            border: none;
            padding: 0.875rem 2rem;
            font-weight: 600;
            border-radius: 12px;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.5);
        }

        .stTextArea textarea {
            background: rgba(30, 41, 59, 0.8);
            border: 2px solid var(--border);
            border-radius: 12px;
            color: var(--text-primary);
        }

        .metric-card {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(34, 211, 238, 0.1) 100%);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .metric-label {
            font-size: 0.875rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        .metric-good { color: #10b981; }
        .metric-warn { color: #f59e0b; }
        .metric-bad { color: #ef4444; }

        .nav-logo {
            font-size: 1.75rem;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 2rem;
        }

        .feature-card {
            background: var(--bg-glass);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
        }

        .feature-icon { font-size: 3rem; margin-bottom: 1rem; }
        .feature-title { font-size: 1.25rem; font-weight: 600; color: var(--text-primary); }
        .feature-desc { color: var(--text-secondary); }

        .stat-number { font-size: 2.5rem; font-weight: 700; color: var(--accent); }
        .stat-label { color: var(--text-secondary); font-size: 0.9rem; }

        .glass-card-sm {
            background: var(--bg-glass);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            border: 1px solid var(--border);
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)


# === PAGE FUNCTIONS ===

def page_home():
    st.markdown("""
    <div class="glass-card" style="text-align: center; padding: 4rem 2rem;">
        <h1 class="hero-title">Trap</h1>
        <p class="hero-subtitle">
            Transform messy FOG invoices into clean, structured data.<br>
            Built for grease trap service operators who demand efficiency.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    stats = [("10+", "Fields Extracted"), ("99%", "Accuracy Rate"), ("< 1s", "Parse Time"), ("∞", "Invoices")]
    for col, (num, label) in zip([col1, col2, col3, col4], stats):
        with col:
            st.markdown(f"""
            <div class="glass-card-sm" style="text-align: center;">
                <div class="stat-number">{num}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    features = [
        ("📄", "Upload", "Paste text or upload your invoice file"),
        ("⚡", "Parse", "Our engine extracts all key fields instantly"),
        ("📊", "Export", "Download clean JSON or CSV for your systems"),
    ]
    for col, (icon, title, desc) in zip([f1, f2, f3], features):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <div class="feature-title">{title}</div>
                <div class="feature-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


def page_demo():
    st.markdown("""
    <div class="glass-card">
        <h1 class="section-title">Live Demo</h1>
        <p style="color: var(--text-secondary);">Try the parser now. Paste an invoice or use a sample.</p>
    </div>
    """, unsafe_allow_html=True)

    sample_files = sorted(FIXTURES_DIR.glob("*.txt")) if FIXTURES_DIR.exists() else []
    sample_options = {"": "Select a sample..."} | {f.stem: f.stem for f in sample_files}

    col_input, col_output = st.columns([1, 1])

    with col_input:
        st.markdown("### Input")
        sample_choice = st.selectbox("Quick start", options=list(sample_options.keys()),
                                     format_func=lambda x: sample_options[x] if x else "Select a sample...")

        default_text = ""
        if sample_choice:
            sample_path = FIXTURES_DIR / f"{sample_choice}.txt"
            if sample_path.exists():
                default_text = sample_path.read_text(errors="replace")

        input_text = st.text_area("Invoice text", value=default_text, height=300,
                                  placeholder="Paste your invoice text here...")

        uploaded = st.file_uploader("Or upload a .txt file", type=["txt"])
        if uploaded:
            input_text = uploaded.read().decode("utf-8", errors="replace")

        parse_clicked = st.button("Parse Invoice", use_container_width=True)

    with col_output:
        st.markdown("### Results")

        if parse_clicked and input_text.strip():
            result = parse_text_to_record(input_text)

            m1, m2, m3 = st.columns(3)
            score = result.confidence_score
            color = "metric-good" if score >= 70 else "metric-warn" if score >= 40 else "metric-bad"

            with m1:
                st.markdown(f'<div class="metric-card"><div class="metric-value {color}">{score}%</div><div class="metric-label">Confidence</div></div>', unsafe_allow_html=True)
            with m2:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{len(result.extracted_fields)}</div><div class="metric-label">Found</div></div>', unsafe_allow_html=True)
            with m3:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{len(result.missing_fields)}</div><div class="metric-label">Missing</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            record_dict = result.record.to_dict()
            table_data = [{"Field": f.replace("_", " ").title(), "Value": record_dict.get(f) or "—",
                           "": "✅" if record_dict.get(f) else "⚪"} for f in EXPECTED_FIELDS + ["notes"]]
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True, height=280)

            if result.missing_fields:
                with st.expander(f"⚠️ {len(result.missing_fields)} fields not found"):
                    st.markdown(", ".join([f"`{f}`" for f in result.missing_fields]))

            st.markdown("### Export")
            exp1, exp2 = st.columns(2)
            with exp1:
                st.download_button("JSON", data=json.dumps(result.to_dict(), indent=2),
                                   file_name="parsed_invoice.json", mime="application/json", use_container_width=True)
            with exp2:
                st.download_button("CSV", data=pd.DataFrame([record_dict]).to_csv(index=False),
                                   file_name="parsed_invoice.csv", mime="text/csv", use_container_width=True)

        elif parse_clicked:
            st.warning("Please enter some text to parse.")
        else:
            st.markdown("""
            <div style="text-align: center; padding: 4rem 2rem; color: var(--text-secondary);
                        background: rgba(30, 41, 59, 0.5); border-radius: 16px; border: 2px dashed var(--border);">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📋</div>
                <div style="font-size: 1.1rem;">No results yet</div>
                <div style="font-size: 0.9rem; margin-top: 0.5rem;">Select a sample or paste text, then click Parse</div>
            </div>
            """, unsafe_allow_html=True)


def page_about():
    st.markdown("""
    <div class="glass-card">
        <h1 class="section-title">About Trap</h1>
        <p style="color: var(--text-secondary); line-height: 1.8;">
            The FOG (Fats, Oils, and Grease) industry keeps restaurants compliant and operational.
            But too much time is spent on paperwork. <strong style="color: #f1f5f9;">Trap</strong> automates the tedious parts.
        </p>
        <p style="color: var(--text-secondary); line-height: 1.8;">
            Our parsing engine reads invoices in any format, extracts the data you need, and outputs it
            in formats your systems can use. Less data entry. Fewer errors. More time for what matters.
        </p>
    </div>
    """, unsafe_allow_html=True)


# === MAIN APP ===

def main():
    inject_background()
    inject_styles()

    with st.sidebar:
        st.markdown('<div class="nav-logo">TRAP</div>', unsafe_allow_html=True)
        page = st.selectbox("NAVIGATION", options=["Home", "Demo", "About"], index=0)
        st.markdown("<br>" * 3, unsafe_allow_html=True)
        st.markdown('<div style="text-align: center; color: var(--text-secondary); font-size: 0.8rem;"><p>v0.1.0</p></div>', unsafe_allow_html=True)

    pages = {"Home": page_home, "Demo": page_demo, "About": page_about}
    pages[page]()


if __name__ == "__main__":
    main()
