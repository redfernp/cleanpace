# cleanpace.py
import streamlit as st
import pandas as pd
from io import StringIO

st.set_page_config(page_title="CleanPace", page_icon="🐎")
st.title("🐎 CleanPace – Run Style Cleaner")

st.write("Paste or upload your run style data below. The app will extract only **Horse**, **Lto1–Lto5** and let you download a clean CSV.")

# Option 1: Paste raw text
text_input = st.text_area("Paste your Run Style Figure data here (optional if uploading a file):", height=250)

# Option 2: File upload
uploaded = st.file_uploader("Or upload a TSV/CSV file", type=["tsv", "csv", "txt"])

# Process input
if text_input or uploaded:
    if uploaded:
        raw = uploaded.read().decode("utf-8")
    else:
        raw = text_input

    try:
        # Attempt TSV first, then fallback to CSV
        df = pd.read_csv(StringIO(raw), sep="\t", header=1)
    except Exception:
        df = pd.read_csv(StringIO(raw), header=1)

    # Select target columns
    cols = ["Horse", "Lto1", "Lto2", "Lto3", "Lto4", "Lto5"]
    subset = df[[c for c in cols if c in df.columns]].copy()

    st.subheader("Preview")
    st.dataframe(subset)

    csv = subset.to_csv(index=False)
    st.download_button(
        "💾 Download Clean CSV",
        csv,
        file_name="cleanpace_output.csv",
        mime="text/csv",
    )
else:
    st.info("Paste your data or upload a file to begin.")
