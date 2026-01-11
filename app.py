"""
Trap - Grease Trap Invoice Parser Web App

This is the Streamlit UI for the invoice parser.
It imports the parsing ENGINE from src/trap/parse.py
and provides a friendly interface for users.

WHY THIS FILE EXISTS:
- Provides a web interface for the parser
- Keeps UI code separate from parsing logic
- Can be deployed to Streamlit Community Cloud

TO RUN LOCALLY:
    streamlit run app.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src/ to path so we can import trap.parse
# This is needed when running streamlit from repo root
sys.path.insert(0, str(Path(__file__).parent / "src"))

from trap.parse import EXPECTED_FIELDS, parse_text_to_record

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Trap - Invoice Parser",
    page_icon="🧾",
    layout="centered",
)

# --- HEADER ---
st.title("🧾 Trap Invoice Parser")
st.markdown(
    "Upload or paste a grease trap service invoice/manifest. "
    "The parser extracts structured data you can download as JSON or CSV."
)

st.divider()

# --- SAMPLE DATA LOADER ---
# Load fixture files for "Try a sample" dropdown
FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"
sample_files = sorted(FIXTURES_DIR.glob("*.txt")) if FIXTURES_DIR.exists() else []
sample_options = {f.stem: f for f in sample_files}


# --- INPUT SECTION ---
st.subheader("📄 Input")

# Create tabs for different input methods
tab_paste, tab_upload = st.tabs(["✍️ Paste Text", "📁 Upload File"])

input_text = ""

with tab_paste:
    # Sample dropdown
    if sample_options:
        col1, col2 = st.columns([3, 1])
        with col2:
            sample_choice = st.selectbox(
                "Try a sample",
                options=[""] + list(sample_options.keys()),
                format_func=lambda x: "Select sample..." if x == "" else x,
                key="sample_selector",
            )
        if sample_choice:
            input_text = sample_options[sample_choice].read_text(errors="replace")

    input_text = st.text_area(
        "Paste invoice text here",
        value=input_text,
        height=250,
        placeholder="Paste your invoice or manifest text here...",
        key="paste_input",
    )

with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload a .txt file",
        type=["txt"],
        key="file_upload",
    )
    if uploaded_file is not None:
        input_text = uploaded_file.read().decode("utf-8", errors="replace")
        st.text_area(
            "File contents",
            value=input_text,
            height=200,
            disabled=True,
        )


# --- PARSE BUTTON ---
st.divider()

parse_clicked = st.button("🔍 Parse Invoice", type="primary", use_container_width=True)


# --- RESULTS SECTION ---
if parse_clicked:
    if not input_text.strip():
        st.error("Please provide some text to parse.")
    else:
        # Run the parser
        with st.spinner("Parsing..."):
            result = parse_text_to_record(input_text)

        st.divider()
        st.subheader("📊 Results")

        # --- CONFIDENCE SCORE ---
        col1, col2, col3 = st.columns(3)
        with col1:
            # Color based on score
            if result.confidence_score >= 70:
                score_color = "green"
            elif result.confidence_score >= 40:
                score_color = "orange"
            else:
                score_color = "red"

            st.metric(
                label="Confidence Score",
                value=f"{result.confidence_score}%",
                help="Percentage of expected fields that were found",
            )

        with col2:
            st.metric(
                label="Fields Found",
                value=len(result.extracted_fields),
            )

        with col3:
            st.metric(
                label="Fields Missing",
                value=len(result.missing_fields),
            )

        # --- WARNINGS FOR MISSING FIELDS ---
        if result.missing_fields:
            missing_count = len(result.missing_fields)
            with st.expander(f"⚠️ Missing fields ({missing_count})", expanded=False):
                for field in result.missing_fields:
                    st.write(f"• `{field}`")

        # --- DATA TABLE ---
        st.markdown("#### Extracted Data")

        # Build table data from the record
        record_dict = result.record.to_dict()
        table_data = []
        for field in EXPECTED_FIELDS + ["notes"]:
            value = record_dict.get(field)
            status = "✅" if value else "—"
            table_data.append(
                {
                    "Field": field.replace("_", " ").title(),
                    "Value": value or "",
                    "Status": status,
                }
            )

        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        # --- JSON VIEWER ---
        with st.expander("🔧 Raw JSON", expanded=False):
            st.json(result.to_dict())

        # --- DOWNLOAD BUTTONS ---
        st.markdown("#### 📥 Export")

        col1, col2 = st.columns(2)

        # JSON download
        json_str = json.dumps(result.to_dict(), indent=2)
        with col1:
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name="parsed_invoice.json",
                mime="application/json",
                use_container_width=True,
            )

        # CSV download (single record)
        csv_df = pd.DataFrame([record_dict])
        csv_str = csv_df.to_csv(index=False)
        with col2:
            st.download_button(
                label="Download CSV",
                data=csv_str,
                file_name="parsed_invoice.csv",
                mime="text/csv",
                use_container_width=True,
            )


# --- FOOTER ---
st.divider()
st.caption("Trap v0.1.0 • [GitHub](https://github.com) • Built with Streamlit")
run app.py