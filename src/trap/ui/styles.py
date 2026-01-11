"""
CSS styles for Trap CRM.
"""

import streamlit as st

STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --primary: #6366f1;
        --accent: #22d3ee;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --bg-dark: #0f172a;
        --bg-card: rgba(30, 41, 59, 0.8);
        --bg-glass: rgba(30, 41, 59, 0.7);
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --border: rgba(148, 163, 184, 0.2);
    }

    .stApp { font-family: 'Inter', sans-serif; }

    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid var(--border);
    }

    .nav-logo {
        font-size: 1.75rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, var(--accent) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }

    .page-header {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 0.5rem;
    }

    .page-subtitle {
        color: var(--text-secondary);
        margin-bottom: 1.5rem;
    }

    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.25rem;
        text-align: center;
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .kpi-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .kpi-success { color: var(--success); }
    .kpi-warning { color: var(--warning); }
    .kpi-danger { color: var(--danger); }
    .kpi-primary { color: var(--primary); }
    .kpi-accent { color: var(--accent); }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .status-scheduled { background: rgba(99, 102, 241, 0.2); color: #6366f1; }
    .status-in-progress { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
    .status-completed { background: rgba(16, 185, 129, 0.2); color: #10b981; }
    .status-verified { background: rgba(34, 211, 238, 0.2); color: #22d3ee; }
    .status-invoiced { background: rgba(168, 85, 247, 0.2); color: #a855f7; }
    .status-draft { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
    .status-needs-docs { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

    .card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    .card-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin-bottom: 1rem;
    }

    .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, #4f46e5 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border-radius: 10px;
    }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
    }

    .completeness-bar {
        height: 8px;
        background: var(--border);
        border-radius: 4px;
        overflow: hidden;
    }

    .completeness-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }

    .completeness-100 { background: var(--success); }
    .completeness-75 { background: var(--accent); }
    .completeness-50 { background: var(--warning); }
    .completeness-25 { background: var(--danger); }
</style>
"""


def inject_styles() -> None:
    """Inject CSS styles into the Streamlit app."""
    st.markdown(STYLES, unsafe_allow_html=True)
